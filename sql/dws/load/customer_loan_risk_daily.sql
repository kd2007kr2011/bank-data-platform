
-- ============================================================
-- D18 DWS 客户贷款风险日汇总
--
-- 文件：sql/dws/load/customer_loan_risk_daily.sql
-- 数据库：bank_dev
--
-- 数据来源：
-- dwd.fact_loan_daily
-- dwd.dim_date
--
-- 目标表：
-- dws.dws_customer_loan_risk_daily
--
-- 数据粒度：
-- 一个客户 × 一个统计日期 = 一条记录
--
-- 统计指标：
-- 1. 贷款笔数
-- 2. 贷款总余额
-- 3. 逾期贷款笔数
-- 4. 逾期贷款余额
-- 5. 贷款逾期率
--
-- 统计口径：
-- 1. overdue_days > 0 视为逾期
-- 2. 逾期余额采用逾期贷款全部未偿本金
-- 3. 逾期率 = 逾期余额 / 贷款总余额
-- 4. 分母为 0 时，逾期率记为 0
-- 5. 使用 ON CONFLICT 支持幂等重跑
--
-- ============================================================


BEGIN;


CREATE TABLE IF NOT EXISTS dws.dws_customer_loan_risk_daily (
    business_date DATE NOT NULL,
    customer_key BIGINT NOT NULL,
    loan_count INTEGER NOT NULL DEFAULT 0,
    loan_balance NUMERIC(18,2) NOT NULL DEFAULT 0,
    overdue_loan_count INTEGER NOT NULL DEFAULT 0,
    overdue_balance NUMERIC(18,2) NOT NULL DEFAULT 0,
    overdue_rate NUMERIC(10,6) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (business_date, customer_key)
);


INSERT INTO dws.dws_customer_loan_risk_daily (
    business_date,
    customer_key,
    loan_count,
    loan_balance,
    overdue_loan_count,
    overdue_balance,
    overdue_rate
)
SELECT
    dd.full_date,
    f.customer_key,
    COUNT(*)::INTEGER,
    SUM(f.outstanding_principal),
    COUNT(*) FILTER (
        WHERE f.overdue_days > 0
    )::INTEGER,
    COALESCE(
        SUM(f.outstanding_principal) FILTER (
            WHERE f.overdue_days > 0
        ),
        0
    ),
    COALESCE(
        SUM(f.outstanding_principal) FILTER (
            WHERE f.overdue_days > 0
        ) / NULLIF(SUM(f.outstanding_principal), 0),
        0
    )
FROM dwd.fact_loan_daily f
JOIN dwd.dim_date dd
    ON f.date_key = dd.date_key
GROUP BY
    dd.full_date,
    f.customer_key
ON CONFLICT (business_date, customer_key)
DO UPDATE SET
    loan_count = EXCLUDED.loan_count,
    loan_balance = EXCLUDED.loan_balance,
    overdue_loan_count = EXCLUDED.overdue_loan_count,
    overdue_balance = EXCLUDED.overdue_balance,
    overdue_rate = EXCLUDED.overdue_rate,
    updated_at = CURRENT_TIMESTAMP;


COMMIT;


SELECT *
FROM dws.dws_customer_loan_risk_daily
ORDER BY business_date, customer_key;
