
-- ============================================================
-- D17 DWS 地区交易日汇总
--
-- 文件：sql/dws/load/region_transaction_daily.sql
-- 数据库：bank_dev
-- 目标表：dws.dws_region_transaction_daily
--
-- 数据来源：
--   dwd.fact_transaction
--   dwd.dim_date
--
-- 数据粒度：business_date + region_key
--
-- 统计指标：
--   total_transaction_count：交易总笔数
--   success_count：成功交易笔数
--   success_amount：成功交易总金额
--
-- 统计口径：
--   1. 总交易笔数包含所有交易状态
--   2. 成功交易金额只统计 SUCCESS
--   3. NULL region_key 代表未知地区
--
-- 执行方式：全量重建，支持幂等重跑
-- ============================================================

CREATE SCHEMA IF NOT EXISTS dws;

CREATE TABLE IF NOT EXISTS dws.dws_region_transaction_daily (
    business_date DATE NOT NULL,
    region_key BIGINT,
    total_transaction_count BIGINT NOT NULL DEFAULT 0,
    success_count BIGINT NOT NULL DEFAULT 0,
    success_amount NUMERIC(20,2) NOT NULL DEFAULT 0,
    dw_load_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_dws_region_transaction_daily
        UNIQUE NULLS NOT DISTINCT (
            business_date,
            region_key
        ),

    CONSTRAINT fk_dws_region_transaction_daily_region
        FOREIGN KEY (region_key)
        REFERENCES dwd.dim_region(region_key)
);

BEGIN;

TRUNCATE TABLE dws.dws_region_transaction_daily;

INSERT INTO dws.dws_region_transaction_daily (
    business_date,
    region_key,
    total_transaction_count,
    success_count,
    success_amount
)
SELECT
    dd.full_date,
    ft.region_key,
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
    ft.region_key;

COMMIT;

SELECT
    r.business_date,
    r.region_key,
    COALESCE(dr.region_name, '未知地区') AS region_name,
    r.total_transaction_count,
    r.success_count,
    r.success_amount
FROM dws.dws_region_transaction_daily r
LEFT JOIN dwd.dim_region dr
    ON r.region_key = dr.region_key
ORDER BY
    r.business_date DESC,
    r.region_key NULLS LAST
LIMIT 20;


