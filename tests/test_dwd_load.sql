
SELECT
    'dwd_loan' AS table_name,
    COUNT(*) AS row_count
FROM dwd.dwd_loan

UNION ALL

SELECT
    'dwd_repayment_event',
    COUNT(*)
FROM dwd.dwd_repayment_event

UNION ALL

SELECT
    'dwd_loan_snapshot',
    COUNT(*)
FROM dwd.dwd_loan_snapshot

UNION ALL

SELECT
    'fact_loan_daily',
    COUNT(*)
FROM dwd.fact_loan_daily;