-- 文件：sql/checks/reconciliation.sql

WITH source_data AS (
    SELECT
        transaction_id,
        account_id,
        transaction_type,
        transaction_status,
        amount,
        (transaction_time AT TIME ZONE 'Asia/Shanghai')::date AS business_date
    FROM source.transactions
),

ods_ranked AS (
    SELECT
        transaction_id,
        account_id,
        transaction_type,
        transaction_status,
        amount,
        transaction_time,
        ods_id,
        load_time,
        ROW_NUMBER() OVER (
            PARTITION BY transaction_id
            ORDER BY load_time DESC NULLS LAST, ods_id DESC
        ) AS rn
    FROM ods.ods_transaction
    WHERE transaction_id IS NOT NULL
),

ods_data AS (
    SELECT
        transaction_id,
        account_id,
        transaction_type,
        transaction_status,
        amount,
        (transaction_time AT TIME ZONE 'Asia/Shanghai')::date AS business_date
    FROM ods_ranked
    WHERE rn = 1
),

dwd_data AS (
    SELECT
        transaction_id,
        account_id,
        transaction_type,
        transaction_status,
        amount,
        (transaction_time AT TIME ZONE 'Asia/Shanghai')::date AS business_date
    FROM dwd.dwd_transaction_detail
),

source_summary AS (
    SELECT
        business_date,
        transaction_type,
        transaction_status,
        COUNT(*) AS transaction_count,
        SUM(amount) AS total_amount
    FROM source_data
    GROUP BY business_date, transaction_type, transaction_status
),

ods_summary AS (
    SELECT
        business_date,
        transaction_type,
        transaction_status,
        COUNT(*) AS transaction_count,
        SUM(amount) AS total_amount
    FROM ods_data
    GROUP BY business_date, transaction_type, transaction_status
),

dwd_summary AS (
    SELECT
        business_date,
        transaction_type,
        transaction_status,
        COUNT(*) AS transaction_count,
        SUM(amount) AS total_amount
    FROM dwd_data
    GROUP BY business_date, transaction_type, transaction_status
),

combined AS (
    SELECT
        business_date,
        transaction_type,
        transaction_status,
        transaction_count AS source_count,
        total_amount AS source_amount,
        0::bigint AS ods_count,
        0::numeric AS ods_amount,
        0::bigint AS dwd_count,
        0::numeric AS dwd_amount
    FROM source_summary

    UNION ALL

    SELECT
        business_date,
        transaction_type,
        transaction_status,
        0::bigint,
        0::numeric,
        transaction_count,
        total_amount,
        0::bigint,
        0::numeric
    FROM ods_summary

    UNION ALL

    SELECT
        business_date,
        transaction_type,
        transaction_status,
        0::bigint,
        0::numeric,
        0::bigint,
        0::numeric,
        transaction_count,
        total_amount
    FROM dwd_summary
),

reconciled AS (
    SELECT
        business_date,
        transaction_type,
        transaction_status,
        SUM(source_count) AS source_count,
        SUM(source_amount) AS source_amount,
        SUM(ods_count) AS ods_count,
        SUM(ods_amount) AS ods_amount,
        SUM(dwd_count) AS dwd_count,
        SUM(dwd_amount) AS dwd_amount
    FROM combined
    GROUP BY business_date, transaction_type, transaction_status
)

SELECT
    business_date,
    transaction_type,
    transaction_status,
    source_count,
    source_amount,
    ods_count,
    ods_amount,
    dwd_count,
    dwd_amount,
    ods_count - source_count AS source_ods_count_diff,
    ods_amount - source_amount AS source_ods_amount_diff,
    dwd_count - ods_count AS ods_dwd_count_diff,
    dwd_amount - ods_amount AS ods_dwd_amount_diff,
    CASE
        WHEN source_count = ods_count
         AND source_amount = ods_amount THEN 'PASS'
        ELSE 'WARN'
    END AS source_ods_status,
    CASE
        WHEN ods_count = dwd_count
         AND ods_amount = dwd_amount THEN 'PASS'
        ELSE 'FAIL'
    END AS ods_dwd_status
FROM reconciled
ORDER BY business_date, transaction_type, transaction_status;