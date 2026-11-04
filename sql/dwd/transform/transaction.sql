
WITH source_rows AS MATERIALIZED (
    SELECT
        t.*,
        ROW_NUMBER() OVER (
            PARTITION BY t.transaction_id
            ORDER BY
                t.updated_at DESC NULLS LAST,
                t.loaded_at DESC NULLS LAST,
                t.batch_id DESC
        ) AS rn
    FROM ods.transaction_current t
),

classified AS MATERIALIZED (
    SELECT
        s.*,
        CASE
            WHEN s.transaction_id IS NULL
                THEN 'NULL_TRANSACTION_ID'
            WHEN s.account_id IS NULL
                THEN 'NULL_ACCOUNT_ID'
            WHEN NOT EXISTS (
                SELECT 1
                FROM source.accounts a
                WHERE a.account_id = s.account_id
            )
                THEN 'INVALID_ACCOUNT'
            WHEN s.amount IS NULL OR s.amount <= 0
                THEN 'INVALID_AMOUNT'
            WHEN s.transaction_type NOT IN (
                'DEPOSIT',
                'WITHDRAWAL',
                'TRANSFER'
            ) OR s.transaction_type IS NULL
                THEN 'INVALID_TRANSACTION_TYPE'
            WHEN s.transaction_status NOT IN (
                'PENDING',
                'SUCCESS',
                'FAILED',
                'CANCELLED',
                'REVERSED'
            ) OR s.transaction_status IS NULL
                THEN 'INVALID_TRANSACTION_STATUS'
            WHEN s.transaction_time IS NULL
                THEN 'INVALID_TRANSACTION_TIME'
            WHEN s.created_at IS NULL
                THEN 'INVALID_CREATED_AT'
            WHEN s.updated_at IS NULL
                THEN 'INVALID_UPDATED_AT'
            WHEN s.batch_id IS NULL
                THEN 'NULL_BATCH_ID'
            WHEN s.loaded_at IS NULL
                THEN 'NULL_LOADED_AT'
            ELSE NULL
        END AS reject_code
    FROM source_rows s
),

valid_rows AS MATERIALIZED (
    SELECT *
    FROM classified
    WHERE rn = 1
      AND reject_code IS NULL
),

rejected AS (
    INSERT INTO ods.rejected_records (
        source_table,
        batch_id,
        source_record_key,
        raw_data,
        rule_code,
        reject_reason,
        record_hash
    )
    SELECT
        'dwd.dwd_transaction_detail',
        batch_id::TEXT,
        COALESCE(transaction_id::TEXT, 'NULL'),
        to_jsonb(c),
        reject_code,
        'D12 DWD 规范化检查未通过：' || reject_code,
        md5(
            COALESCE(transaction_id::TEXT, 'NULL')
            || '|'
            || reject_code
            || '|'
            || COALESCE(batch_id::TEXT, '')
        )
    FROM classified c
    WHERE rn = 1
      AND reject_code IS NOT NULL
    ON CONFLICT (source_table, record_hash, rule_code)
    DO NOTHING
    RETURNING 1
),

upserted AS (
    INSERT INTO dwd.dwd_transaction_detail (
        transaction_id,
        account_id,
        transaction_type,
        amount,
        transaction_status,
        transaction_time,
        transaction_date,
        source_created_at,
        source_batch_id,
        ods_load_time,
        source_updated_at,
        dw_load_time
    )
    SELECT
        transaction_id,
        account_id,
        transaction_type,
        amount::NUMERIC(18, 2),
        transaction_status,
        transaction_time,
        (transaction_time AT TIME ZONE 'Asia/Shanghai')::DATE,
        created_at,
        batch_id::TEXT,
        loaded_at,
        updated_at,
        CURRENT_TIMESTAMP
    FROM valid_rows
    ON CONFLICT (transaction_id)
    DO UPDATE SET
        account_id = EXCLUDED.account_id,
        transaction_type = EXCLUDED.transaction_type,
        amount = EXCLUDED.amount,
        transaction_status = EXCLUDED.transaction_status,
        transaction_time = EXCLUDED.transaction_time,
        transaction_date = EXCLUDED.transaction_date,
        source_created_at = EXCLUDED.source_created_at,
        source_batch_id = EXCLUDED.source_batch_id,
        ods_load_time = EXCLUDED.ods_load_time,
        source_updated_at = EXCLUDED.source_updated_at,
        dw_load_time = CURRENT_TIMESTAMP
    WHERE
        dwd.dwd_transaction_detail.source_updated_at IS NULL
        OR EXCLUDED.source_updated_at >
           dwd.dwd_transaction_detail.source_updated_at
    RETURNING transaction_id
)

SELECT
    (SELECT COUNT(*) FROM source_rows) AS source_count,
    (
        SELECT COUNT(*)
        FROM classified
        WHERE rn > 1
    ) AS duplicate_count,
    (
        SELECT COUNT(*)
        FROM classified
        WHERE rn = 1
          AND reject_code IS NOT NULL
    ) AS invalid_count,
    (
        SELECT COUNT(*)
        FROM valid_rows
    ) AS eligible_count,
    (
        SELECT COUNT(*)
        FROM rejected
    ) AS newly_rejected_count,
    (
        SELECT COUNT(*)
        FROM upserted
    ) AS dwd_changed_count;
