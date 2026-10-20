
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def main():
    # 1. 定位项目根目录和配置文件
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"

    if not env_path.is_file():
        print(f"配置文件不存在：{env_path}")
        sys.exit(1)

    load_dotenv(env_path)

    # 2. 读取数据库配置
    try:
        config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "dbname": os.getenv("DB_NAME", "bank_dev"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD"),
            "connect_timeout": 5,
        }
    except ValueError:
        print("配置错误：DB_PORT 必须是整数。")
        sys.exit(1)

    if not 1 <= config["port"] <= 65535:
        print("配置错误：DB_PORT 必须在 1 到 65535 之间。")
        sys.exit(1)

    if not config["password"]:
        print("配置错误：请在 .env 中设置 DB_PASSWORD。")
        sys.exit(1)

    # 3. 尝试连接 PostgreSQL
    try:
        with psycopg.connect(**config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        version()
                    """)

                row = cur.fetchone()

                if row is None:
                    raise RuntimeError("数据库连接成功，但查询没有返回结果")

                database, user, version = row

        print("数据库连接成功！")
        print(f"数据库名称：{database}")
        print(f"连接用户：{user}")
        print(f"数据库版本：{version}")

    except psycopg.OperationalError as exc:
        print("数据库连接失败，请检查 PostgreSQL 是否启动、"
              "端口是否正确以及连接参数是否正确。")
        print(f"错误详情：{exc}")
        sys.exit(1)

    except psycopg.Error as exc:
        print("数据库查询失败。")
        print(f"错误详情：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
