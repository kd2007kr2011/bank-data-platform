
"""D10: Source -> ODS 交易数据增量抽取。

基于 updated_at + Watermark + Overlap Window。
本文件只负责抽取，不写入 ODS，也不推进水位线。
"""

import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv


# ==================================================
# 1. 配置
# ==================================================

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

JOB_NAME = "transactions_incremental"

# 重叠窗口：5 分钟
OVERLAP_MINUTES = 5

# 每次从数据库读取的记录数量
BATCH_SIZE = 1000

# 首次同步的初始水位线（根据实际历史数据调整）
INITIAL_WATERMARK = datetime(
    2020, 1, 1, tzinfo=timezone.utc
)


# ==================================================
# 2. 连接数据库
# ==================================================

def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "bank_dev"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


# ==================================================
# 3. 查询上一次成功的 Watermark
# ==================================================

def get_last_watermark(conn):
    sql = """
        SELECT watermark_end
        FROM metadata.etl_runs
        WHERE job_name = %s
          AND status = 'SUCCESS'
        ORDER BY watermark_end DESC
        LIMIT 1
    """

    with conn.cursor() as cur:
        cur.execute(sql, (JOB_NAME,))
        result = cur.fetchone()

    if result is None or result[0] is None:
        print("没有成功同步记录，使用初始水位线")
        return INITIAL_WATERMARK

    return result[0]


# ==================================================
# 4. 计算本次增量抽取区间
# ==================================================

def get_extract_window(last_watermark):
    # 从上次成功水位线往前回退
    start_time = last_watermark - timedelta(
        minutes=OVERLAP_MINUTES
    )

    # 不早于初始水位线
    start_time = max(start_time, INITIAL_WATERMARK)

    # 固定本次抽取的结束边界
    end_time = datetime.now(timezone.utc)

    if start_time >= end_time:
        raise ValueError("抽取起点不得晚于或等于终点")

    return start_time, end_time


# ==================================================
# 5. 使用 fetchmany 分批抽取
# ==================================================

def extract_incremental(conn, start_time, end_time):
    sql = """
        SELECT
            transaction_id,
            account_id,
            transaction_type,
            amount,
            transaction_status,
            transaction_time,
            created_at,
            updated_at
        FROM source.transactions
        WHERE updated_at >= %s
          AND updated_at < %s
        ORDER BY updated_at, transaction_id
    """

    # 使用 PostgreSQL 服务端游标
    with conn.cursor(
        name="incremental_transactions_cursor"
    ) as cur:

        cur.execute(sql, (start_time, end_time))

        while True:
            rows = cur.fetchmany(BATCH_SIZE)

            if not rows:
                break

            yield rows


# ==================================================
# 6. 主程序：验证增量抽取
# ==================================================

def main():
    total_rows = 0
    batch_count = 0

    with get_connection() as conn:

        # 第一步：读取上一次成功水位线
        last_watermark = get_last_watermark(conn)

        # 第二步：计算抽取窗口
        start_time, end_time = get_extract_window(
            last_watermark
        )

        print("=" * 60)
        print("D10 交易数据增量抽取")
        print("=" * 60)
        print(f"任务名称: {JOB_NAME}")
        print(f"上次水位线: {last_watermark}")
        print(f"本次起点: {start_time}")
        print(f"本次终点: {end_time}")
        print(f"重叠窗口: {OVERLAP_MINUTES} 分钟")

        # 第三步：分批抽取
        for rows in extract_incremental(
            conn, start_time, end_time
        ):
            batch_count += 1
            total_rows += len(rows)

            print(
                f"批次 {batch_count}: "
                f"抽取 {len(rows)} 行"
            )

            # D10 当前阶段仅验证抽取
            # 后续在这里交给 load_incremental.py

        print("=" * 60)
        print(f"总批次数: {batch_count}")
        print(f"总抽取行数: {total_rows}")
        print("增量抽取完成（尚未装载 ODS）")
        print("=" * 60)


if __name__ == "__main__":
    main()
