-- ============================================================
-- D17 DWS 客户交易日汇总
--
-- 文件：sql/dws/load/customer_transaction_daily.sql
-- 数据库：bank_dev
-- 目标表：dws.dws_customer_transaction_daily
--
-- 数据来源：
--   dwd.fact_transaction
--   dwd.dim_date
--
-- 数据粒度：business_date + customer_key
-- 执行方式：全量重建，支持幂等重跑
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS dws;

CREATE TABLE IF NOT EXISTS dws.dws_customer_transaction_daily (
    business_date DATE NOT NULL,
    customer_key BIGINT NOT NULL,
    total_transaction_count BIGINT NOT NULL DEFAULT 0,
    success_count BIGINT NOT NULL DEFAULT 0,
    success_amount NUMERIC(20,2) NOT NULL DEFAULT 0,
    dw_load_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (business_date, customer_key)
);

TRUNCATE TABLE dws.dws_customer_transaction_daily;

INSERT INTO dws.dws_customer_transaction_daily (
    business_date,
    customer_key,
    total_transaction_count,
    success_count,
    success_amount
)
SELECT
    dd.full_date,
    ft.customer_key,
    COUNT(*),
    COUNT(*) FILTER (
        WHERE ft.transaction_status = 'SUCCESS'
    ),
    COALESCE(
        SUM(ft.amount) FILTER (
            WHERE ft.transaction_status = 'SUCCESS'
        ),
        0
    )
FROM dwd.fact_transaction ft
JOIN dwd.dim_date dd
    ON ft.date_key = dd.date_key
GROUP BY
    dd.full_date,
    ft.customer_key;

COMMIT;

