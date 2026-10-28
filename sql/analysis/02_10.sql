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