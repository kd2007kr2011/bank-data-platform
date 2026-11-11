-- 客户与账户的关联查询：内连接下每个客户名下有哪些账户。
-- 文件：sql/analysis/customer/customer_account_join.sql

-- 1. 取客户及其名下账户的全部字段
SELECT
    a.*
FROM source.customers AS a
JOIN source.accounts AS b
    ON a.customer_id = b.customer_id;

-- 2. 只取客户与账户标识
SELECT
    source.customers.customer_id,
    source.accounts.account_id
FROM source.customers
INNER JOIN source.accounts
    ON source.customers.customer_id = source.accounts.customer_id;

-- 3. 同上，并按客户编号排序
SELECT
    source.customers.customer_id,
    source.accounts.account_id
FROM source.customers
JOIN source.accounts
    ON source.customers.customer_id = source.accounts.customer_id
ORDER BY source.customers.customer_id ASC;
