"""D11: Source -> ODS 交易增量装载，增加数据质量检查与坏数据隔离。

流程：
1. 读取上一次成功的 Watermark
2. 分批抽取 source.transactions
3. 执行 ODS 数据质量规则
4. 正常数据幂等写入 ods.transaction_current
5. 异常数据写入 ods.rejected_records
6. 所有目标写入与 SUCCESS 状态在同一事务提交
7. 失败时回滚目标写入，并独立记录 FAILED
"""

import hashlib
import json
import sys
from pathlib import Path


# 直接执行 etl/ 下的脚本时，sys.path 只包含 etl/ 目录，
# 需要把项目根目录加入 sys.path 才能导入 scripts 包。
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from psycopg.types.json import Jsonb

from extract_incremental import (
    JOB_NAME,
    get_connection,
    get_last_watermark,
    get_extract_window,
    extract_incremental,
)
from scripts.quality.ods_rules import check_transaction_quality


# ==================================================
# 1. 配置
# ==================================================

SOURCE_TABLE = "source.transactions"

SOURCE_COLUMNS = (
    "transaction_id",
    "account_id",
    "transaction_type",
    "amount",
    "transaction_status",
    "transaction_time",
    "created_at",
    "updated_at",
)


# ==================================================
# 2. SQL：ODS 幂等写入
# ==================================================

UPSERT_SQL = """
    INSERT INTO ods.transaction_current (
        transaction_id,
        account_id,
        transaction_type,
        amount,
        transaction_status,
        transaction_time,
        created_at,
        updated_at,
        batch_id,
        loaded_at
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, CURRENT_TIMESTAMP
    )
    ON CONFLICT (transaction_id)
    DO UPDATE SET
        account_id = EXCLUDED.account_id,
        transaction_type = EXCLUDED.transaction_type,
        amount = EXCLUDED.amount,
        transaction_status = EXCLUDED.transaction_status,
        transaction_time = EXCLUDED.transaction_time,
        created_at = EXCLUDED.created_at,
        updated_at = EXCLUDED.updated_at,
        batch_id = EXCLUDED.batch_id,
        loaded_at = CURRENT_TIMESTAMP
    WHERE EXCLUDED.updated_at >
          ods.transaction_current.updated_at
"""


REJECT_SQL = """
    INSERT INTO ods.rejected_records (
        source_table,
        batch_id,
        source_record_key,
        raw_data,
        rule_code,
        reject_reason,
        record_hash
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (source_table, record_hash, rule_code)
    DO NOTHING
"""


# ==================================================
# 3. 创建 ETL 运行记录
# ==================================================

def create_etl_run(conn, start_time, end_time):
    sql = """
        INSERT INTO metadata.etl_runs (
            job_name,
            status,
            watermark_start,
            watermark_end,
            started_at
        )
        VALUES (%s, 'RUNNING', %s, %s, CURRENT_TIMESTAMP)
        RETURNING run_id
    """

    with conn.cursor() as cur:
        cur.execute(sql, (JOB_NAME, start_time, end_time))
        run_id = cur.fetchone()[0]

    return run_id


# ==================================================
# 4. 记录成功状态
# ==================================================

def mark_success(conn, run_id, extracted, loaded):
    sql = """
        UPDATE metadata.etl_runs
        SET
            status = 'SUCCESS',
            finished_at = CURRENT_TIMESTAMP,
            rows_extracted = %s,
            rows_loaded = %s,
            error_message = NULL
        WHERE run_id = %s
          AND status = 'RUNNING'
    """

    with conn.cursor() as cur:
        cur.execute(sql, (extracted, loaded, run_id))

        if cur.rowcount != 1:
            raise RuntimeError(
                f"无法更新成功状态: run_id={run_id}"
            )


# ==================================================
# 5. 记录失败状态
# ==================================================

def mark_failed(conn, run_id, error_message):
    sql = """
        UPDATE metadata.etl_runs
        SET
            status = 'FAILED',
            finished_at = CURRENT_TIMESTAMP,
            error_message = %s
        WHERE run_id = %s
          AND status = 'RUNNING'
    """

    with conn.cursor() as cur:
        cur.execute(sql, (str(error_message)[:5000], run_id))


# ==================================================
# 6. 查询有效账户
# ==================================================

def get_valid_account_ids(conn):
    """从 Source 账户主表读取账户 ID，避免在规则中硬编码。"""
    with conn.cursor() as cur:
        cur.execute("SELECT account_id FROM source.accounts")
        return {row[0] for row in cur.fetchall()}


# ==================================================
# 7. 拒收记录写入
# ==================================================

def make_json_safe_record(record):
    """将 Decimal、datetime 等类型规范化为 JSON 可序列化的数据。"""
    serialized = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return serialized, json.loads(serialized)


def save_rejected_records(conn, rejected_records, run_id):
    """写入拒收记录；返回本次实际新增的拒收明细数。"""
    if not rejected_records:
        return 0

    values = []

    for item in rejected_records:
        raw_json, raw_data = make_json_safe_record(item["raw_data"])
        record_hash = hashlib.sha256(
            raw_json.encode("utf-8")
        ).hexdigest()

        transaction_id = raw_data.get("transaction_id")
        source_record_key = (
            str(transaction_id)
            if transaction_id is not None
            else None
        )

        values.append((
            SOURCE_TABLE,
            str(run_id),
            source_record_key,
            Jsonb(raw_data),
            item["rule_code"],
            item["reject_reason"],
            record_hash,
        ))

    with conn.cursor() as cur:
        cur.executemany(REJECT_SQL, values)
        # PostgreSQL + psycopg executemany 的 rowcount 是受影响行数；
        # ON CONFLICT DO NOTHING 的冲突行不计入新增数。
        return cur.rowcount


# ==================================================
# 8. 单批次质量检查与装载
# ==================================================

def load_batch(conn, rows, run_id, valid_account_ids):
    """
    返回：
    loaded_count：ODS 实际插入/更新行数
    rejected_count：本批质量规则识别出的拒收明细数
    rejected_inserted：本批实际新增到拒收表的明细数
    """
    if not rows:
        return 0, 0, 0

    records = [
        dict(zip(SOURCE_COLUMNS, row))
        for row in rows
    ]

    valid_records, rejected_records = check_transaction_quality(
        records,
        valid_account_ids,
    )

    # 先保存异常数据。和正常 ODS 写入处于同一数据库事务，
    # 后续任一写入失败，拒收记录也会随事务回滚。
    rejected_inserted = save_rejected_records(
        conn,
        rejected_records,
        run_id,
    )

    # 只有通过质量检查的数据才进入正常 ODS 表
    values = [
        tuple(record[column] for column in SOURCE_COLUMNS)
        + (run_id,)
        for record in valid_records
    ]

    loaded_count = 0

    if values:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, values)
            loaded_count = cur.rowcount

    return loaded_count, len(rejected_records), rejected_inserted


# ==================================================
# 9. 主程序：增量抽取 + 质量检查 + 装载
# ==================================================

def main():
    total_extracted = 0
    total_loaded = 0
    total_rejected = 0
    total_rejected_inserted = 0
    batch_count = 0

    # 先创建并提交 RUNNING 记录，失败时才能独立记录 FAILED
    with get_connection() as metadata_conn:
        last_watermark = get_last_watermark(metadata_conn)
        start_time, end_time = get_extract_window(last_watermark)

        run_id = create_etl_run(
            metadata_conn,
            start_time,
            end_time,
        )
        metadata_conn.commit()

        print("=" * 60)
        print("D11: 交易增量同步 + ODS 质量检查")
        print("=" * 60)
        print(f"Run ID: {run_id}")
        print(f"上次水位线: {last_watermark}")
        print(f"抽取开始: {start_time}")
        print(f"抽取结束: {end_time}")

        try:
            with get_connection() as source_conn:
                with get_connection() as target_conn:
                    # Source 和 Target 使用同一个数据库时，
                    # 从账户主表读取有效账户 ID。
                    valid_account_ids = get_valid_account_ids(target_conn)

                    batches = extract_incremental(
                        source_conn,
                        start_time,
                        end_time,
                    )

                    for rows in batches:
                        batch_count += 1
                        loaded, rejected, rejected_inserted = load_batch(
                            target_conn,
                            rows,
                            run_id,
                            valid_account_ids,
                        )

                        total_extracted += len(rows)
                        total_loaded += loaded
                        total_rejected += rejected
                        total_rejected_inserted += rejected_inserted

                        print(
                            f"批次 {batch_count}: "
                            f"抽取 {len(rows)} 行, "
                            f"ODS 写入/更新 {loaded} 行, "
                            f"识别拒收明细 {rejected} 条, "
                            f"新增拒收明细 {rejected_inserted} 条"
                        )

                    # SUCCESS 状态与 ODS / 拒收表写入同一事务提交。
                    mark_success(
                        target_conn,
                        run_id,
                        total_extracted,
                        total_loaded,
                    )
                    target_conn.commit()

        except Exception as exc:
            # 目标事务中尚未提交的 ODS、拒收记录、SUCCESS 状态均回滚。
            # RUNNING 记录此前已独立提交，因此可更新为 FAILED。
            metadata_conn.rollback()
            mark_failed(metadata_conn, run_id, str(exc))
            metadata_conn.commit()

            print(f"ETL 执行失败: {exc}")
            raise

        print("=" * 60)
        print("增量同步成功")
        print(f"Run ID: {run_id}")
        print(f"总批次数: {batch_count}")
        print(f"抽取记录数: {total_extracted}")
        print(f"ODS 实际写入/更新数: {total_loaded}")
        print(f"质量规则识别拒收明细数: {total_rejected}")
        print(f"拒收表实际新增明细数: {total_rejected_inserted}")
        print(f"Watermark 已推进至: {end_time}")
        print("=" * 60)


if __name__ == "__main__":
    main()
