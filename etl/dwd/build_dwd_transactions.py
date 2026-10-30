
from pathlib import Path
import os
import sys

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env")

SQL_PATH = ROOT / "sql" / "dwd" / "transaction.sql"


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "bank_dev"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def load_sql():
    if not SQL_PATH.exists():
        raise FileNotFoundError(
            f"SQL 文件不存在：{SQL_PATH}"
        )

    return SQL_PATH.read_text(encoding="utf-8")


def build_dwd():

    sql_text = load_sql()

    print("=" * 60)
    print("D12 DWD 交易明细构建")
    print("=" * 60)

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(sql_text)

            result = cur.fetchone()

            if result is None:
                raise RuntimeError("SQL 未返回对账结果")

            (
                source_count,
                duplicate_count,
                invalid_count,
                eligible_count,
                newly_rejected_count,
                dwd_changed_count,
            ) = result

            print("\n数据处理统计")
            print("-" * 60)

            print(f"ODS 来源记录数：{source_count}")
            print(f"重复淘汰记录数：{duplicate_count}")
            print(f"质量拒收记录数：{invalid_count}")
            print(f"有效候选记录数：{eligible_count}")
            print(f"新增拒收记录数：{newly_rejected_count}")
            print(f"DWD 实际变更数：{dwd_changed_count}")

            accounted_count = (
                duplicate_count
                + invalid_count
                + eligible_count
            )

            print("\n数据对账检查")
            print("-" * 60)

            if source_count != accounted_count:
                raise ValueError(
                    f"来源记录与处理结果无法对账："
                    f"{source_count} != {accounted_count}"
                )

            print("来源记录对账通过")

            cur.execute("""
                SELECT COUNT(*)
                FROM (
                    SELECT transaction_id
                    FROM dwd.dwd_transaction_detail
                    GROUP BY transaction_id
                    HAVING COUNT(*) > 1
                ) t;
            """)

            duplicate_dwd = cur.fetchone()[0]

            if duplicate_dwd > 0:
                raise ValueError(
                    f"DWD 存在重复业务键：{duplicate_dwd}"
                )

            print("DWD 业务键唯一性检查通过")

            cur.execute("""
                SELECT COUNT(*)
                FROM dwd.dwd_transaction_detail
                WHERE transaction_id IS NULL
                   OR account_id IS NULL
                   OR amount <= 0
                   OR transaction_type NOT IN (
                       'DEPOSIT',
                       'WITHDRAWAL',
                       'TRANSFER'
                   )
                   OR transaction_status NOT IN (
                       'PENDING',
                       'SUCCESS',
                       'FAILED',
                       'CANCELLED',
                       'REVERSED'
                   );
            """)

            invalid_dwd = cur.fetchone()[0]

            if invalid_dwd > 0:
                raise ValueError(
                    f"DWD 存在不规范数据：{invalid_dwd}"
                )

            print("DWD 金额、类型与状态检查通过")

    print("\n" + "=" * 60)
    print("D12 DWD 构建成功，事务已提交")
    print("=" * 60)


if __name__ == "__main__":

    try:
        build_dwd()

    except Exception as exc:
        print("\nDWD 构建失败")
        print(f"错误原因：{exc}")
        sys.exit(1)
