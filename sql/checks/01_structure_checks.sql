-- 1. 检查实际 Source 字段（上传文件是字段字典，不是数据库实测结果）
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='source'
  AND table_name IN ('transactions','loans','loan_disbursements','loan_repayments')
ORDER BY table_name, ordinal_position;

-- 2. 新建三张表是否存在
SELECT table_schema, table_name
FROM information_schema.tables
WHERE (table_schema='ods' AND table_name='ods_transaction')
   OR (table_schema='dwd' AND table_name IN ('dwd_transaction_detail','dwd_loan_snapshot'))
ORDER BY table_schema, table_name;

-- 3. 字段和类型
SELECT table_schema, table_name, ordinal_position, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE (table_schema='ods' AND table_name='ods_transaction')
   OR (table_schema='dwd' AND table_name IN ('dwd_transaction_detail','dwd_loan_snapshot'))
ORDER BY table_schema, table_name, ordinal_position;

-- 4. 主键、唯一性与 CHECK 约束
SELECT n.nspname AS schema_name, c.relname AS table_name,
       con.conname AS constraint_name, pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE (n.nspname='ods' AND c.relname='ods_transaction')
   OR (n.nspname='dwd' AND c.relname IN ('dwd_transaction_detail','dwd_loan_snapshot'))
ORDER BY 1,2,3;

-- 5. 载入后可检查实际行数（未运行 ETL 时预期为零）
SELECT 'ods_transaction' AS table_name, COUNT(*) AS row_count FROM ods.ods_transaction
UNION ALL SELECT 'dwd_transaction_detail', COUNT(*) FROM dwd.dwd_transaction_detail
UNION ALL SELECT 'dwd_loan_snapshot', COUNT(*) FROM dwd.dwd_loan_snapshot;
