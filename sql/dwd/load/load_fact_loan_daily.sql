
-- ============================================================
-- D18 DWD 贷款日事实表数据装载
--
-- 文件：sql/dwd/load/load_fact_loan_daily.sql
-- 数据库：bank_dev
--
-- 数据来源：
-- dwd.dwd_loan_snapshot
-- dwd.dwd_loan
-- dwd.dim_customer
-- dwd.dim_date
--
-- 目标表：
-- dwd.fact_loan_daily
--
-- 数据粒度：
-- 一笔贷款 × 一个统计日期 = 一条记录
--
-- 处理逻辑：
-- 1. 读取贷款每日快照
-- 2. 通过 loan_id 关联贷款合同，获取 customer_id
-- 3. 关联客户维度，获取 customer_key 和 region_key
-- 4. 关联日期维度，获取 date_key
-- 5. 将数据装载到贷款日事实表
-- 6. 使用 ON CONFLICT 实现幂等重跑
-- 7. 检查装载结果及维度关联完整性
--
-- 注意：
-- 贷款快照表的 overdue_days 当前为空时使用 0。
-- 后续完善还款计划及逾期判断规则后再更新。
--
-- ============================================================


BEGIN;

INSERT INTO dwd.fact_loan_daily (
    loan_id,
    customer_key,
    region_key,
    date_key,
    total_disbursed,
    total_repaid_principal,
    outstanding_principal,
    overdue_days,
    created_at,
    updated_at
)
SELECT
    s.loan_id::VARCHAR(64),
    dc.customer_key,
    dc.region_key,
    dd.date_key,
    s.total_disbursed,
    s.total_principal_repaid,
    s.outstanding_principal,
    COALESCE(s.overdue_days, 0),
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM dwd.dwd_loan_snapshot s
LEFT JOIN dwd.dwd_loan l
    ON l.loan_id = s.loan_id
LEFT JOIN dwd.dim_customer dc
    ON dc.customer_id = l.customer_id::VARCHAR
LEFT JOIN dwd.dim_date dd
    ON dd.full_date = s.snapshot_date
ON CONFLICT (loan_id, date_key)
DO UPDATE SET
    customer_key = EXCLUDED.customer_key,
    region_key = EXCLUDED.region_key,
    total_disbursed = EXCLUDED.total_disbursed,
    total_repaid_principal = EXCLUDED.total_repaid_principal,
    outstanding_principal = EXCLUDED.outstanding_principal,
    overdue_days = EXCLUDED.overdue_days,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;


SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT loan_id) AS total_loans,
    COUNT(DISTINCT date_key) AS total_snapshot_dates,
    SUM(total_disbursed) AS total_disbursed,
    SUM(total_repaid_principal) AS total_repaid_principal,
    SUM(outstanding_principal) AS total_outstanding_principal,
    SUM(
        CASE
            WHEN overdue_days > 0
            THEN outstanding_principal
            ELSE 0
        END
    ) AS total_overdue_balance
FROM dwd.fact_loan_daily;


SELECT
    COUNT(*) FILTER (
        WHERE dc.customer_key IS NULL
    ) AS missing_customer,
    COUNT(*) FILTER (
        WHERE dd.date_key IS NULL
    ) AS missing_date
FROM dwd.dwd_loan_snapshot s
LEFT JOIN dwd.dwd_loan l
    ON l.loan_id = s.loan_id
LEFT JOIN dwd.dim_customer dc
    ON dc.customer_id = l.customer_id::VARCHAR
LEFT JOIN dwd.dim_date dd
    ON dd.full_date = s.snapshot_date;
