
from pathlib import Path
import os
import csv

import psycopg
from psycopg import sql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent
DATA_DIR = ROOT / "data" / "generated"
ENV_PATH = PROJECT_ROOT / ".env"

if not ENV_PATH.is_file():
    raise SystemExit(f"配置文件不存在：{ENV_PATH}")

load_dotenv(ENV_PATH)

TABLES = [
    ("customers", "customer_id"),
    ("accounts", "account_id"),
    ("transactions", "transaction_id"),
    ("loans", "loan_id"),
    ("loan_disbursements", "disbursement_id"),
    ("loan_repayments", "repayment_id"),
]

# 本脚本会清空目标库，只允许指向开发库
DEV_DB = "bank_dev"


def main():
    # 1. 导入前检查：数据文件和数据库配置
    missing = [
        f"{table}.csv"
        for table, _ in TABLES
        if not (DATA_DIR / f"{table}.csv").is_file()
    ]

    if missing:
        raise SystemExit(
            "缺少数据文件："
            + ", ".join(missing)
            + f"\n请先运行：python scripts/generate/generate.py"
        )

    db_name = os.getenv("DB_NAME", DEV_DB)
    password = os.getenv("DB_PASSWORD")

    if not password:
        raise SystemExit("配置错误：请在 .env 中设置 DB_PASSWORD。")

    if db_name != DEV_DB:
        raise SystemExit(
            f"配置错误：DB_NAME 只能指向开发库 {DEV_DB}，当前为 {db_name}。"
        )

    with psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=db_name,
        user=os.getenv("DB_USER", "postgres"),
        password=password,
    ) as conn:

        # 2. 防止误操作其他数据库
        row = conn.execute("SELECT current_database()").fetchone()

        if row is None:
            raise RuntimeError("无法获取当前数据库名称")

        current_db = row[0]

        if current_db != DEV_DB:
            raise RuntimeError(
                f"禁止清空非开发数据库：{current_db}"
            )

        # 整个清空与导入过程使用一个事务
        with conn.transaction():

            # 1. 清空六张源业务表
            print("正在清空原有数据...")

            conn.execute("""
                TRUNCATE TABLE
                    source.loan_repayments,
                    source.loan_disbursements,
                    source.transactions,
                    source.loans,
                    source.accounts,
                    source.customers
                RESTART IDENTITY
                RESTRICT;
            """)

            print("原有数据已清空")

            # 2. 按外键依赖顺序导入
            for table, pk in TABLES:
                path = DATA_DIR / f"{table}.csv"

                with path.open(
                    "r",
                    encoding="utf-8-sig",
                    newline=""
                ) as f:
                    columns = next(csv.reader(f))

                statement = sql.SQL(
                    "COPY {} ({}) FROM STDIN "
                    "WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')"
                ).format(
                    sql.Identifier("source", table),
                    sql.SQL(", ").join(
                        sql.Identifier(c) for c in columns
                    ),
                )

                with path.open("rb") as f:
                    with conn.cursor() as cur:
                        with cur.copy(statement) as copy:
                            while chunk := f.read(1024 * 1024):
                                copy.write(chunk)

                count_row = conn.execute(
                    sql.SQL(
                        "SELECT COUNT(*) FROM {}"
                    ).format(
                        sql.Identifier("source", table)
                    )
                ).fetchone()

                count = count_row[0] if count_row else 0

                print(f"{table}: 已导入 {count} 条")

                if count == 0:
                    raise RuntimeError(
                        f"{table}.csv 没有数据，已回滚本次导入"
                    )

            # 3. 同步六张表的自增序列
            for table, pk in TABLES:
                seq_row = conn.execute(
                    "SELECT pg_get_serial_sequence(%s, %s)",
                    (f"source.{table}", pk),
                ).fetchone()

                sequence = seq_row[0] if seq_row else None

                if sequence is None:
                    # 主键不是 IDENTITY/SERIAL 时跳过
                    print(f"{table}: 未找到自增序列，跳过序列同步")
                    continue

                max_row = conn.execute(
                    sql.SQL(
                        "SELECT MAX({}) FROM {}"
                    ).format(
                        sql.Identifier(pk),
                        sql.Identifier("source", table),
                    )
                ).fetchone()

                max_id = max_row[0] if max_row else None

                if max_id is not None:
                    conn.execute(
                        "SELECT setval(%s, %s, true)",
                        (sequence, max_id),
                    )

        print("\n全部数据重新导入成功！")


if __name__ == "__main__":
    main()
