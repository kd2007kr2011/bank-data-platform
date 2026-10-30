-- 查看 ODS 交易表的字段信息
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'ods'
  AND table_name = 'ods_transaction'
ORDER BY ordinal_position;


SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'dwd'
  AND table_name = 'dwd_transaction_detail'
ORDER BY ordinal_position;

SELECT
    con.conname,
    con.contype,
    pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con
WHERE con.conrelid =
      'dwd.dwd_transaction_detail'::regclass;



SELECT
    transaction_id,
    amount,
    load_time,
    ROW_NUMBER() OVER (
        PARTITION BY transaction_id
        ORDER BY load_time DESC
    ) AS rn
FROM ods.ods_transaction;