
"""Source -> ODS 交易表全量批次装载。"""

import os
from pathlib import Path
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv

from extract_full import extract_transactions


# 项目根目录
ROOT = Path(__file__).resolve().parents[1]

# 加载数据库配置
load_dotenv(ROOT / ".env")


# ===== 装载参数（直接在代码中修改）=====

# 本次导入批次标识，重跑同一个 batch_id 会先删除该批次旧数据
BATCH_ID = "batch_20261026"

# 每批抽取/写入的记录数
BATCH_SIZE = 1000

# 是否模拟失败，用于验证事务回滚
SIMULATE_FAILURE = False

# ====================================


def get_connection():
    """建立 PostgreSQL 数据库连接。"""

    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def load_transactions(
    batch_id=BATCH_ID,
    batch_size=BATCH_SIZE,
    simulate_failure=SIMULATE_FAILURE
):
    """
    将 Source 交易表全量装载到 ODS。

    同一个 batch_id 重跑：
    删除该批次原有记录，再重新插入。

    不同 batch_id：
    保留历史批次。
    """

    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id 不能为空")

    if batch_size <= 0:
        raise ValueError("batch_size 必须大于 0")

    # 每次执行的装载时间
    load_time = datetime.now(timezone.utc)

    source_system = "bank_core"

    insert_sql = """
        INSERT INTO ods.ods_transaction (
            transaction_id,
            account_id,
            transaction_type,
            amount,
            transaction_status,
            transaction_time,
            created_at,
            batch_id,
            load_time,
            source_system
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
    """

    total_rows = 0

    # 成功离开连接上下文时自动提交
    # 出现异常时自动回滚
    with get_connection() as conn:

        # 设置一致性快照隔离级别
        conn.execute(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
        )

        # 防止相同批次并发执行
        conn.execute(
            "SELECT pg_advisory_xact_lock("
            "hashtext(%s), hashtext(%s))",
            ("ods.ods_transaction", batch_id)
        )

        with conn.cursor() as cur:

            # 删除当前批次旧数据
            # 不影响其他 batch_id
            cur.execute(
                """
                DELETE FROM ods.ods_transaction
                WHERE batch_id = %s
                """,
                (batch_id,)
            )

            # 从 Source 分批抽取
            for rows in extract_transactions(
                conn,
                batch_size=batch_size
            ):

                # 为每条源记录增加装载元数据
                ods_rows = [
                    tuple(row) + (
                        batch_id,
                        load_time,
                        source_system
                    )
                    for row in rows
                ]

                # 批量写入
                cur.executemany(
                    insert_sql,
                    ods_rows
                )

                total_rows += len(ods_rows)

                print(
                    f"当前批次已写入 {total_rows} 条"
                )

                # 测试事务回滚
                if simulate_failure:
                    raise RuntimeError(
                        "模拟 ETL 失败，触发事务回滚"
                    )

            # 校验 Source 数据总数
            cur.execute(
                "SELECT COUNT(*) FROM source.transactions"
            )

            result = cur.fetchone()

            if result is None:
                raise RuntimeError("查询 Source 记录数失败")

            source_count = result[0]
            # 校验本次 ODS 批次的数据量
            cur.execute(
                """
                SELECT COUNT(*)
                FROM ods.ods_transaction
                WHERE batch_id = %s
                """,
                (batch_id,)
            )

            result = cur.fetchone()

            if result is None:
                raise RuntimeError("查询 ODS 记录数失败")

            ods_count = result[0]

            if total_rows != source_count:
                raise ValueError(
                    "抽取数量与 Source 总数不一致"
                )

            if ods_count != source_count:
                raise ValueError(
                    "ODS 装载数量与 Source 总数不一致"
                )

    # 到达这里，说明事务已经成功提交
    print("=" * 50)
    print("ODS 全量批次装载成功")
    print(f"batch_id: {batch_id}")
    print(f"source_count: {source_count}")
    print(f"ods_count: {ods_count}")
    print("=" * 50)


def main():

    # 参数在文件顶部配置，直接执行即可
    load_transactions()


if __name__ == "__main__":
    main()
