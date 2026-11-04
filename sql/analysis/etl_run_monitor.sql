-- ETL 运行监控：查看最近几次增量抽取的运行状态、水位线与数据量。

SELECT
    run_id,
    status,
    watermark_start,
    watermark_end,
    rows_extracted,
    rows_loaded
FROM metadata.etl_runs
ORDER BY run_id DESC
LIMIT 5;
