-- ============================================================
-- D15 交易事实表数据装载
--
-- 文件：sql/dwd/load_fact_transaction.sql
-- 数据库：bank_dev
-- 目标表：dwd.fact_transaction
--
-- 数据来源：
--   dwd.dwd_transaction_detail
--   source.accounts
--   dwd.dim_customer
--   dwd.dim_date
--
-- 数据粒度：一笔交易一行
-- 执行方式：UPSERT，支持幂等重跑
-- 状态范围：PENDING / SUCCESS / FAILED
-- 时间口径：Asia/Shanghai
-- ============================================================

INSERT INTO dwd.fact_transaction (
    transaction_id,
    customer_key,
    region_key,
    date_key,
    account_id,
    transaction_time,
    transaction_type,
    transaction_status,
    amount
)
SELECT
    t.transaction_id::VARCHAR(64),
    c.customer_key,
    c.region_key,
    d.date_key,
    t.account_id::VARCHAR(64),
    t.transaction_time AT TIME ZONE 'Asia/Shanghai',
    t.transaction_type,
    t.transaction_status,
    t.amount
FROM dwd.dwd_transaction_detail AS t
INNER JOIN source.accounts AS a
    ON t.account_id = a.account_id
INNER JOIN dwd.dim_customer AS c
    ON a.customer_id::VARCHAR(64) = c.customer_id
INNER JOIN dwd.dim_date AS d
    ON t.transaction_date = d.full_date
WHERE t.transaction_status IN (
    'PENDING',
    'SUCCESS',
    'FAILED'
)
ON CONFLICT (transaction_id)
DO UPDATE SET
    customer_key = EXCLUDED.customer_key,
    region_key = EXCLUDED.region_key,
    date_key = EXCLUDED.date_key,
    account_id = EXCLUDED.account_id,
    transaction_time = EXCLUDED.transaction_time,
    transaction_type = EXCLUDED.transaction_type,
    transaction_status = EXCLUDED.transaction_status,
    amount = EXCLUDED.amount,
    updated_at = CURRENT_TIMESTAMP;