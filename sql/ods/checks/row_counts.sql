-- 数据量对比：源层交易数与 ODS 交易数。
-- 文件：sql/ods/checks/row_counts.sql

SELECT COUNT(*)
FROM source.transactions;

SELECT COUNT(*)
FROM ods.ods_transaction;
