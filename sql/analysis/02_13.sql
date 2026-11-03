
WITH total_amount_loan as(
    SELECT
        ld.loan_id,
        sum(ld.disbursement_amount) as disb_amount
    FROM  source.loan_disbursements ld
    WHERE ld.disbursement_status = 'SUCCESS'
    GROUP BY ld.loan_id
),
total_amount_repay as (
    SELECT
        lr.loan_id,
        SUM(lr.principal_amount) as repay_amount
    FROM source.loan_repayments lr
    WHERE lr.repayment_status = 'SUCCESS'
    GROUP BY lr.loan_id
)
SELECT
    tal.loan_id,
    COALESCE(tal.disb_amount,0) - COALESCE(tar.repay_amount,0) as output_amount
FROM total_amount_loan tal
left JOIN total_amount_repay tar
ON tal.loan_id = tar.loan_id

