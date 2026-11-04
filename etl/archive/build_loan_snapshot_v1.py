"""【历史归档】贷款快照的一次性生成脚本。

已由 `etl/dwd/build_loan_snapshot.py` 取代：当前版本支持幂等重跑、
历史回补与重跑审计。此文件保留，用于说明 SQL 文件的调用方式。
"""

import os
from pathlib import Path
from datetime import date

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

SQL_PATH = ROOT / "sql" / "dwd" / "transform" / "loan_snapshot.sql"

SNAPSHOT_DATE = date(2026, 10, 31)


def main():
    # 1. 动态读取并拼接连接串（兼容单独配置或 DATABASE_URL 配置）
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_host = os.environ.get("DB_HOST", "localhost")
        db_port = os.environ.get("DB_PORT", "5432")
        db_name = os.environ.get("DB_NAME", "bank_dev")
        db_user = os.environ.get("DB_USER", "postgres")
        db_password = os.environ.get("DB_PASSWORD", "")
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    sql = SQL_PATH.read_text(encoding="utf-8")

    # 2. 连接数据库并执行
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {"snapshot_date": SNAPSHOT_DATE}
            )
            print(f"快照新增/变更：{cur.rowcount}")
        
        # 3. 使用 with 块时，若无异常会自动 commit，
        # 但显式调用一次 conn.commit() 也可以确保写入生效
        conn.commit()

    print(f"{SNAPSHOT_DATE} 贷款快照生成成功")


if __name__ == "__main__":
    main()