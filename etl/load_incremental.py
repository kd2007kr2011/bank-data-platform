
"""D10: Source -> ODS 交易增量装载。

功能：
1. 读取上一次成功的 Watermark
2. 调用 extract_incremental.py 分批抽取
3. 使用 ON CONFLICT 实现幂等装载
4. 保存 metadata.etl_runs 运行状态
5. ODS 写入成功后才推进 Watermark

要求：
- source.transactions 已有 updated_at
- metadata.etl_runs 已创建
- ods.transaction_current 已创建
"""

from datetime import datetime, timezone

from extract_incremental import (
    JOB_NAME,
    get_connection,
    get_last_watermark,
    get_extract_window,
    extract_incremental,
)


# ==================================================
# 1. 装载配置
# ==================================================

# 可以直接运行本文件
# 也可以从其他 Python 文件导入 main()


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

    -- 只有 Source 版本更新，才修改 ODS
    WHERE EXCLUDED.updated_at >
          ods.transaction_current.updated_at
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
        VALUES (
            %s, 'RUNNING', %s, %s, CURRENT_TIMESTAMP
        )
        RETURNING run_id
    """

    with conn.cursor() as cur:
        cur.execute(
            sql,
            (JOB_NAME, start_time, end_time)
        )
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
        cur.execute(
            sql,
            (extracted, loaded, run_id)
        )

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
        cur.execute(
            sql,
            (str(error_message)[:5000], run_id)
        )


# ==================================================
# 6. 单批次装载
# ==================================================

def load_batch(conn, rows, run_id):
    if not rows:
        return 0

    # Source 每行有 8 个字段
    # 额外增加一个 batch_id
    values = [
        tuple(row) + (run_id,)
        for row in rows
    ]

    with conn.cursor() as cur:
        cur.executemany(UPSERT_SQL, values)

        # 实际插入或更新的记录数
        return cur.rowcount


# ==================================================
# 7. 主程序：增量抽取 + 装载
# ==================================================

def main():
    total_extracted = 0
    total_loaded = 0
    batch_count = 0

    # 元数据连接：用于独立保存 RUNNING / FAILED
    with get_connection() as metadata_conn:

        # 第一步：查询上次成功水位线
        last_watermark = get_last_watermark(
            metadata_conn
        )

        start_time, end_time = get_extract_window(
            last_watermark
        )

        # 第二步：创建运行记录
        run_id = create_etl_run(
            metadata_conn,
            start_time,
            end_time
        )

        metadata_conn.commit()

        print("=" * 60)
        print("D10: 交易增量同步")
        print("=" * 60)
        print(f"Run ID: {run_id}")
        print(f"上次水位线: {last_watermark}")
        print(f"抽取开始: {start_time}")
        print(f"抽取结束: {end_time}")

        try:
            # 读取和写入分别使用数据库连接
            with get_connection() as source_conn:
                with get_connection() as target_conn:

                    # 第三步：增量抽取
                    batches = extract_incremental(
                        source_conn,
                        start_time,
                        end_time
                    )

                    for rows in batches:
                        batch_count += 1

                        # 第四步：装载本批数据
                        loaded = load_batch(
                            target_conn,
                            rows,
                            run_id
                        )

                        total_extracted += len(rows)
                        total_loaded += loaded

                        print(
                            f"批次 {batch_count}: "
                            f"抽取 {len(rows)} 行, "
                            f"写入/更新 {loaded} 行"
                        )

                    # 第五步：装载成功后更新状态
                    # 与 ODS 写入使用同一个事务
                    mark_success(
                        target_conn,
                        run_id,
                        total_extracted,
                        total_loaded
                    )

                    # 第六步：一起提交
                    target_conn.commit()

        except Exception as exc:

            # target_conn 的未提交写入会回滚
            # 单独记录失败，不推进成功水位线
            metadata_conn.rollback()

            mark_failed(
                metadata_conn,
                run_id,
                str(exc)
            )

            metadata_conn.commit()

            print(f"ETL 执行失败: {exc}")
            raise

        print("=" * 60)
        print("增量同步成功")
        print(f"Run ID: {run_id}")
        print(f"总批次数: {batch_count}")
        print(f"抽取记录数: {total_extracted}")
        print(f"实际写入/更新数: {total_loaded}")
        print(f"Watermark 已推进至: {end_time}")
        print("=" * 60)


if __name__ == "__main__":
    main()
