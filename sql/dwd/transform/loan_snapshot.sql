-- 贷款快照加工 SQL（生产口径）。
-- 使用 psycopg 的命名占位符 %(snapshot_date)s，需由 Python 驱动，不可直接用 psql 执行：
--   .venv/Scripts/python etl/dwd/build_loan_snapshot.py
-- 可重跑、可回补的版本见 etl/dwd/build_loan_snapshot.py。

WITH params AS (
    SELECT 
        %(snapshot_date)s::DATE AS snapshot_date,
        (%(snapshot_date)s::DATE + INTERVAL '1 day')::TIMESTAMP 
            AT TIME ZONE 'Asia/Shanghai' AS cutoff_time
),
disbursed AS (
    SELECT 
        d.loan_id,
        SUM(d.disbursement_amount) AS total_disbursed
    FROM source.loan_disbursements d
    CROSS JOIN params p
    WHERE d.disbursement_status = 'SUCCESS'
      AND d.disbursement_time < p.cutoff_time
    GROUP BY d.loan_id
),
repaid AS (
    SELECT 
        r.loan_id,
        SUM(r.principal_amount) AS total_repaid,
        SUM(r.interest_amount) AS total_interest
    FROM dwd.dwd_repayment_event r
    CROSS JOIN params p
    WHERE r.repayment_status = 'SUCCESS'
      AND r.repayment_time < p.cutoff_time
    GROUP BY r.loan_id
),
calculated AS (
    SELECT 
        p.snapshot_date,
        l.loan_id,
        COALESCE(d.total_disbursed, 0) AS total_disbursed,
        COALESCE(r.total_repaid, 0) AS total_principal_repaid,
        COALESCE(r.total_interest, 0) AS total_interest_paid,
        COALESCE(d.total_disbursed, 0) - COALESCE(r.total_repaid, 0) AS outstanding_principal
    FROM dwd.dwd_loan l
    CROSS JOIN params p
    LEFT JOIN disbursed d ON l.loan_id = d.loan_id
    LEFT JOIN repaid r ON l.loan_id = r.loan_id
    WHERE l.contract_date <= p.snapshot_date
)
INSERT INTO dwd.dwd_loan_snapshot (
    snapshot_date,
    loan_id,
    total_disbursed,
    total_principal_repaid,
    total_interest_paid,
    outstanding_principal,
    overdue_days
)
SELECT 
    snapshot_date,
    loan_id,
    total_disbursed,
    total_principal_repaid,
    total_interest_paid,
    outstanding_principal,
    NULL AS overdue_days
FROM calculated
ON CONFLICT (snapshot_date, loan_id)
DO UPDATE SET 
    total_disbursed = EXCLUDED.total_disbursed,
    total_principal_repaid = EXCLUDED.total_principal_repaid,
    total_interest_paid = EXCLUDED.total_interest_paid,
    outstanding_principal = EXCLUDED.outstanding_principal,
    overdue_days = EXCLUDED.overdue_days,
    etl_updated_at = CURRENT_TIMESTAMP
WHERE (
    dwd.dwd_loan_snapshot.total_disbursed,
    dwd.dwd_loan_snapshot.total_principal_repaid,
    dwd.dwd_loan_snapshot.total_interest_paid,
    dwd.dwd_loan_snapshot.outstanding_principal,
    dwd.dwd_loan_snapshot.overdue_days
) IS DISTINCT FROM (
    EXCLUDED.total_disbursed,
    EXCLUDED.total_principal_repaid,
    EXCLUDED.total_interest_paid,
    EXCLUDED.outstanding_principal,
    EXCLUDED.overdue_days
);