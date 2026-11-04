
"""ODS 增量装载集成测试：质量检查、拒收入库、重复执行去重。

依赖数据库，需先准备好 source.accounts 的账户数据。
"""

import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from etl.load.load_incremental import (
    get_connection,
    get_valid_account_ids,
    load_batch,
)


TEST_BATCH_ID = "ODS_QUALITY_INTEGRATION_TEST"


def build_test_rows(valid_account_id, invalid_account_id):
    """构造四类异常；重复 ID 冲突会产生两条拒收明细。"""

    now = datetime.now(timezone.utc)

    return [
        # 异常 1：交易 ID 为空
        (
            None,
            valid_account_id,
            "DEPOSIT",
            Decimal("100.00"),
            "SUCCESS",
            now,
            now,
            now,
        ),

        # 异常 2：账户不存在
        (
            900000000000001,
            invalid_account_id,
            "DEPOSIT",
            Decimal("200.00"),
            "SUCCESS",
            now,
            now,
            now,
        ),

        # 异常 3：交易时间格式错误
        (
            900000000000002,
            valid_account_id,
            "DEPOSIT",
            Decimal("300.00"),
            "SUCCESS",
            "not-a-date",
            now,
            now,
        ),

        # 异常 4：相同交易 ID 对应不同金额
        (
            900000000000003,
            valid_account_id,
            "DEPOSIT",
            Decimal("400.00"),
            "SUCCESS",
            now,
            now,
            now,
        ),
        (
            900000000000003,
            valid_account_id,
            "DEPOSIT",
            Decimal("500.00"),
            "SUCCESS",
            now,
            now,
            now,
        ),
    ]


class TestOdsQualityIntegration(unittest.TestCase):

    def setUp(self):
        self.conn = get_connection()

        # 清理上次测试可能留下的同批次记录
        with self.conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM ods.rejected_records
                WHERE batch_id = %s
                """,
                (TEST_BATCH_ID,),
            )
        self.conn.commit()

        # 使用真实账户 ID，避免把正常账户误判为异常
        self.valid_account_ids = get_valid_account_ids(self.conn)

        if not self.valid_account_ids:
            raise RuntimeError(
                "source.accounts 没有账户数据，请先准备测试账户"
            )

        valid_account_id = next(iter(self.valid_account_ids))

        invalid_account_id = -900000000000001
        while invalid_account_id in self.valid_account_ids:
            invalid_account_id -= 1

        self.rows = build_test_rows(
            valid_account_id,
            invalid_account_id,
        )

    def tearDown(self):
        """测试数据不长期留在拒收表中。"""

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM ods.rejected_records
                    WHERE batch_id = %s
                    """,
                    (TEST_BATCH_ID,),
                )
            self.conn.commit()
        finally:
            self.conn.close()

    def load(self):
        """执行一次装载并提交。"""

        result = load_batch(
            self.conn,
            self.rows,
            TEST_BATCH_ID,
            self.valid_account_ids,
        )
        self.conn.commit()
        return result

    def rejected_counts(self):
        """按规则统计拒收表明细。"""

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    rule_code,
                    COUNT(*) AS detail_count
                FROM ods.rejected_records
                WHERE batch_id = %s
                GROUP BY rule_code
                """,
                (TEST_BATCH_ID,),
            )
            return dict(cur.fetchall())

    def rejected_total(self):
        """拒收表中本批次的记录总数。"""

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM ods.rejected_records
                WHERE batch_id = %s
                """,
                (TEST_BATCH_ID,),
            )
            return cur.fetchone()[0]

    def test_01_invalid_rows_are_not_loaded(self):
        """异常数据不进入正常 ODS。"""

        loaded, rejected, inserted = self.load()

        self.assertEqual(loaded, 0)
        self.assertEqual(rejected, 5)
        self.assertEqual(inserted, 5)

    def test_02_repeat_run_is_idempotent(self):
        """重复执行同一批数据不新增拒收明细。"""

        self.load()

        loaded, rejected, inserted = self.load()

        self.assertEqual(loaded, 0)
        self.assertEqual(rejected, 5)
        self.assertEqual(inserted, 0)
        self.assertEqual(self.rejected_total(), 5)

    def test_03_rule_breakdown(self):
        """四类规则全部命中，数量符合预期。"""

        self.load()

        rule_counts = self.rejected_counts()

        self.assertEqual(
            rule_counts.get("NULL_TRANSACTION_ID"), 1
        )
        self.assertEqual(
            rule_counts.get("INVALID_ACCOUNT"), 1
        )
        self.assertEqual(
            rule_counts.get("INVALID_TRANSACTION_TIME"), 1
        )
        self.assertEqual(
            rule_counts.get("DUPLICATE_TRANSACTION_ID"), 2
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
