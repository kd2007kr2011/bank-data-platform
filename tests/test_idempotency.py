
"""贷款快照的幂等性、历史重跑和事务回滚测试。"""

import sys
import unittest

from pathlib import Path
from decimal import Decimal

from psycopg.errors import CheckViolation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from etl.dwd.build_loan_snapshot import (
    get_connection,
    build_snapshot,
)


TEST_DATE = "2026-11-02"


class TestIdempotency(unittest.TestCase):

    def setUp(self):
        """每个测试创建独立的临时数据表。"""

        self.conn = get_connection()

        with self.conn.cursor() as cur:

            cur.execute("""
                CREATE TEMP TABLE loan_disbursements (
                    loan_id VARCHAR(30),
                    disbursement_amount NUMERIC(18,2),
                    disbursement_time TIMESTAMP,
                    disbursement_status VARCHAR(20)
                )
            """)

            cur.execute("""
                CREATE TEMP TABLE loan_repayments (
                    loan_id VARCHAR(30),
                    principal_amount NUMERIC(18,2),
                    repayment_time TIMESTAMP,
                    repayment_status VARCHAR(20)
                )
            """)

            cur.execute("""
                CREATE TEMP TABLE loan_snapshot (
                    snapshot_date DATE NOT NULL,
                    loan_id VARCHAR(30) NOT NULL,
                    total_disbursed NUMERIC(18,2) NOT NULL,
                    total_repaid NUMERIC(18,2) NOT NULL,
                    outstanding_principal NUMERIC(18,2)
                        NOT NULL CHECK (
                            outstanding_principal >= 0
                        ),
                    PRIMARY KEY (snapshot_date, loan_id)
                )
            """)

            # 构造两笔贷款
            cur.execute("""
                INSERT INTO loan_disbursements
                VALUES
                ('L001',100000,'2026-11-01','SUCCESS'),
                ('L002',200000,'2026-11-01','SUCCESS')
            """)

            # 构造还款
            cur.execute("""
                INSERT INTO loan_repayments
                VALUES
                ('L001',30000,'2026-11-02','SUCCESS'),
                ('L002',50000,'2026-11-02','SUCCESS')
            """)

    def tearDown(self):
        """关闭连接，临时表自动删除。"""
        self.conn.close()

    def run_etl(self):
        """调用 D14 ETL，使用临时表。"""

        return build_snapshot(
            self.conn,
            TEST_DATE,
            source_schema="pg_temp",
            target_schema="pg_temp",
            target_table="loan_snapshot",
            audit_schema=None,
            reason="unit_test",
        )

    def get_snapshot(self):
        """读取所有测试快照。"""

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT
                    snapshot_date,
                    loan_id,
                    total_disbursed,
                    total_repaid,
                    outstanding_principal
                FROM pg_temp.loan_snapshot
                ORDER BY loan_id
            """)

            return cur.fetchall()

    def test_01_idempotency(self):
        """相同业务日执行两次，结果不变。"""

        self.run_etl()

        first_result = self.get_snapshot()

        self.run_etl()

        second_result = self.get_snapshot()

        self.assertEqual(
            first_result,
            second_result
        )

        self.assertEqual(
            len(second_result),
            2
        )

    def test_02_history_replay(self):
        """补录历史还款后，重新计算余额。"""

        self.run_etl()

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT outstanding_principal
                FROM pg_temp.loan_snapshot
                WHERE loan_id = 'L001'
            """)

            old_balance = cur.fetchone()[0]

            # 模拟发现一笔漏记的历史还款
            cur.execute("""
                INSERT INTO pg_temp.loan_repayments
                VALUES (
                    'L001',
                    5000,
                    '2026-11-02',
                    'SUCCESS'
                )
            """)

        # 重新执行同一天的快照
        self.run_etl()

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT outstanding_principal
                FROM pg_temp.loan_snapshot
                WHERE loan_id = 'L001'
            """)

            new_balance = cur.fetchone()[0]

        self.assertEqual(
            old_balance,
            Decimal("70000.00")
        )

        self.assertEqual(
            new_balance,
            Decimal("65000.00")
        )

    def test_03_transaction_rollback(self):
        """中途发生错误，旧快照必须保留。"""

        self.run_etl()

        before = self.get_snapshot()

        # 制造异常：还款总额超过放款总额
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pg_temp.loan_repayments
                VALUES (
                    'L001',
                    200000,
                    '2026-11-02',
                    'SUCCESS'
                )
            """)

        # 新快照无法通过 CHECK 约束
        with self.assertRaises(CheckViolation):
            self.run_etl()

        # 验证 DELETE 也已经回滚
        after = self.get_snapshot()

        self.assertEqual(before, after)

    def test_04_unique_business_key(self):
        """检查贷款快照业务键唯一性。"""

        self.run_etl()
        self.run_etl()

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT
                    snapshot_date,
                    loan_id,
                    COUNT(*)
                FROM pg_temp.loan_snapshot
                GROUP BY snapshot_date, loan_id
                HAVING COUNT(*) > 1
            """)

            duplicates = cur.fetchall()

        self.assertEqual(duplicates, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
