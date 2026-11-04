-- 数据量对比：源层交易数与 ODS 交易数。

SELECT COUNT(*)
FROM source.transactions;

SELECT COUNT(*)
FROM ods.ods_transaction;
