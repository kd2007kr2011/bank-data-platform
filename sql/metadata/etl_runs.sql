CREATE SCHEMA IF NOT EXISTS metadata;

CREATE TABLE if not EXISTS metadata.etl_runs(
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    job_name VARCHAR(100) NOT NULL,

    status VARCHAR(20) NOT NULL
        CHECK(status IN ('RUNNING','SUCCESS','FAILED')),

    watermark_start TIMESTAMPTZ,
    watermark_end TIMESTAMPTZ,

    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ,

    rows_extracted BIGINT DEFAULT 0,
    rows_loaded BIGINT DEFAULT 0,

    error_message TEXT

)


SELECT
    watermark_end
FROM metadata.etl_runs
WHERE job_name = 'transactions_incremental'
  AND status = 'SUCCESS'
ORDER BY watermark_end DESC
LIMIT 1;