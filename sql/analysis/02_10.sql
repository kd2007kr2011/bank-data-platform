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

SELECT
    transaction_id,
    COUNT(*) AS cnt
FROM ods.transaction_current
GROUP BY transaction_id
HAVING COUNT(*) > 1;