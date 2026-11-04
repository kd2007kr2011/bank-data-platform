-- 没有账户的客户：左连接后取 account_id 为空的行。

-- 1. 带客户全部字段
SELECT
    source.customers.customer_id,
    source.customers.customer_name,
    source.accounts.account_id
FROM source.customers
LEFT JOIN source.accounts
    ON source.customers.customer_id = source.accounts.customer_id
WHERE source.accounts.account_id IS NULL;

-- 2. 只取去重后的客户编号
SELECT DISTINCT
    source.customers.customer_id
FROM source.customers
LEFT JOIN source.accounts
    ON source.customers.customer_id = source.accounts.customer_id
WHERE source.accounts.account_id IS NULL;
