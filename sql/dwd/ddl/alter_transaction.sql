
-- D12：调整 DWD 交易表的追溯字段

ALTER TABLE dwd.dwd_transaction_detail
    DROP COLUMN IF EXISTS ods_id;

ALTER TABLE dwd.dwd_transaction_detail
    ADD COLUMN IF NOT EXISTS source_updated_at TIMESTAMPTZ;

-- 检查表结构
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'dwd'
  AND table_name = 'dwd_transaction_detail'
ORDER BY ordinal_position;
