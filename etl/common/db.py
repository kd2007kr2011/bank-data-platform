"""统一的 PostgreSQL 连接工厂。

所有 ETL 脚本都从这里取连接，避免各处重复实现导致的配置不一致：
- 若设置了 `DATABASE_URL`，优先使用它；
- 否则回退到 `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD`。
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# 项目根目录：etl/common/db.py -> etl/common -> etl -> 项目根
ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env")


def get_connection(autocommit=False):
    """建立 PostgreSQL 数据库连接。

    参数：
        autocommit: 是否开启自动提交。默认 False，由调用方显式提交/回滚。
    """

    db_url = os.environ.get("DATABASE_URL")

    if db_url:
        return psycopg.connect(db_url, autocommit=autocommit)

    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "bank_dev"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        autocommit=autocommit,
    )
