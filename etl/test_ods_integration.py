
"""D11 集成测试：质量检查、拒收入库、重复执行去重。"""

from datetime import datetime, timezone
from decimal import Decimal

from load_incremental_d11 import (
    get_connection,
    get_valid_account_ids,
    load_batch,
)


TEST_BATCH_ID = "D11_QUALITY_INTEGRATION_TEST"


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


def main():
    conn = get_connection()

    try:
        # 清理上次测试可能留下的同批次记录
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM ods.rejected_records
                WHERE batch_id = %s
                """,
                (TEST_BATCH_ID,),
            )
        conn.commit()

        # 使用真实账户 ID，避免把正常账户误判为异常
        valid_account_ids = get_valid_account_ids(conn)

        if not valid_account_ids:
            raise RuntimeError(
                "source.accounts 没有账户数据，请先准备测试账户"
            )

        valid_account_id = next(iter(valid_account_ids))

        invalid_account_id = -900000000000001
        while invalid_account_id in valid_account_ids:
            invalid_account_id -= 1

        rows = build_test_rows(
            valid_account_id,
            invalid_account_id,
        )

        print("=" * 60)
        print("D11 质量检查集成测试")
        print("=" * 60)

        # 第一次执行：应写入 5 条拒收明细
        loaded1, rejected1, inserted1 = load_batch(
            conn,
            rows,
            TEST_BATCH_ID,
            valid_account_ids,
        )
        conn.commit()

        print("\n第一次执行")
        print(f"正常装载数：{loaded1}")
        print(f"识别拒收明细：{rejected1}")
        print(f"实际新增拒收明细：{inserted1}")

        # 第二次执行完全相同的数据
        loaded2, rejected2, inserted2 = load_batch(
            conn,
            rows,
            TEST_BATCH_ID,
            valid_account_ids,
        )
        conn.commit()

        print("\n第二次重复执行")
        print(f"正常装载数：{loaded2}")
        print(f"识别拒收明细：{rejected2}")
        print(f"实际新增拒收明细：{inserted2}")

        # 检查数据库中的真实记录
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    rule_code,
                    COUNT(*) AS detail_count
                FROM ods.rejected_records
                WHERE batch_id = %s
                GROUP BY rule_code
                ORDER BY rule_code
                """,
                (TEST_BATCH_ID,),
            )
            results = cur.fetchall()

            cur.execute(
                """
                SELECT COUNT(*)
                FROM ods.rejected_records
                WHERE batch_id = %s
                """,
                (TEST_BATCH_ID,),
            )
            total_count = cur.fetchone()[0]

        print("\n数据库拒收明细")
        for rule_code, count in results:
            print(f"{rule_code}: {count}")

        print(f"拒收表总记录数：{total_count}")

        # 断言：四类规则全部命中，重复执行不新增
        assert loaded1 == 0, "异常数据不应进入正常 ODS"
        assert rejected1 == 5, "第一次执行预期识别 5 条拒收明细"
        assert inserted1 == 5, "第一次执行预期新增 5 条拒收明细"
        assert rejected2 == 5, "第二次仍应识别 5 条拒收明细"
        assert inserted2 == 0, "第二次不应新增重复拒收记录"
        assert total_count == 5, "拒收表中应保留 5 条测试明细"

        rule_counts = dict(results)

        assert rule_counts.get("NULL_TRANSACTION_ID") == 1
        assert rule_counts.get("INVALID_ACCOUNT") == 1
        assert rule_counts.get("INVALID_TRANSACTION_TIME") == 1
        assert rule_counts.get("DUPLICATE_TRANSACTION_ID") == 2

        print("\n全部测试通过！")

    finally:
        # 测试数据不长期留在拒收表中
        # try:
        #     conn.rollback()
        #     with conn.cursor() as cur:
        #         cur.execute(
        #             """
        #             DELETE FROM ods.rejected_records
        #             WHERE batch_id = %s
        #             """,
        #             (TEST_BATCH_ID,),
        #         )
        #     conn.commit()
        # finally:
        #     conn.close()
        conn.close()


if __name__ == "__main__":
    main()
