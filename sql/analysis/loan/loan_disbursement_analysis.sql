-- 贷款放款与余额分析：放款规模筛选，以及合同-放款-还款的余额计算。
-- 文件：sql/analysis/loan/loan_disbursement_analysis.sql

-- 1. 单笔放款金额超过 10 万元的贷款
WITH total_disbursed AS (
    SELECT
        source.loan_disbursements.loan_id,
        SUM(source.loan_disbursements.disbursement_amount) AS total_disbursed
    FROM source.loan_disbursements
    GROUP BY source.loan_disbursements.loan_id
)
SELECT *
FROM total_disbursed
WHERE total_disbursed.total_disbursed > 100000
ORDER BY total_disbursed.total_disbursed DESC;

-- 2. 每笔贷款截至 2027-01-01 仍需偿还的金额
WITH total_loan AS (
    SELECT
        ld.loan_id,
        SUM(ld.disbursement_amount) AS loan_amount
    FROM source.loan_disbursements ld
    WHERE ld.disbursement_status = 'SUCCESS'
      AND ld.disbursement_time < '2027-01-01'
    GROUP BY ld.loan_id
),
total_repay AS (
    SELECT
        lr.loan_id,
        SUM(lr.principal_amount) AS repay_amount
    FROM source.loan_repayments lr
    WHERE lr.repayment_status = 'SUCCESS'
      AND lr.repayment_time < '2027-01-01'
    GROUP BY lr.loan_id
)
SELECT
    tl.loan_id,
    COALESCE(tl.loan_amount, 0) - COALESCE(tr.repay_amount, 0) AS need_repay
FROM total_loan tl
JOIN total_repay tr
    ON tl.loan_id = tr.loan_id
WHERE COALESCE(tl.loan_amount, 0) - COALESCE(tr.repay_amount, 0) > 0;

-- 3. 只看成功放款，成功还款后的剩余本金
WITH total_amount_loan AS (
    SELECT
        ld.loan_id,
        SUM(ld.disbursement_amount) AS disb_amount
    FROM source.loan_disbursements ld
    WHERE ld.disbursement_status = 'SUCCESS'
    GROUP BY ld.loan_id
),
total_amount_repay AS (
    SELECT
        lr.loan_id,
        SUM(lr.principal_amount) AS repay_amount
    FROM source.loan_repayments lr
    WHERE lr.repayment_status = 'SUCCESS'
    GROUP BY lr.loan_id
)
SELECT
    tal.loan_id,
    COALESCE(tal.disb_amount, 0) - COALESCE(tar.repay_amount, 0) AS output_amount
FROM total_amount_loan tal
LEFT JOIN total_amount_repay tar
    ON tal.loan_id = tar.loan_id;
