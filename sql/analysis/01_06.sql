SELECT 
    date_trunc('month',transaction_time) as month,
    sum(amount) as total_amount
FROM 
    source.transactions
where extract(year from transaction_time) = 2026
    and extract(month from transaction_time ) in (1,2)
GROUP BY date_trunc('month',transaction_time)
ORDER BY month



select 
    date_trunc('month', transaction_time) as month,
    sum(amount) as amount
from source.transactions
GROUP BY date_trunc('month',transaction_time)
ORDER BY amount DESC


SELECT
    a.*
FROM
    customers as a
JOIN accounts AS b 
ON a.customer_id = b.customer_id

select
    SOURCE.customers.customer_id,
    SOURCE.accounts.account_id
FROM
    source.customers
INNER JOIN SOURCE.accounts
 ON source.customers.customer_id = source.accounts.customer_id

 
SELECT 
    source.customers.customer_id,
    source.accounts.account_id
FROM source.customers
JOIN source.accounts
ON source.customers.customer_id = source.accounts.customer_id
ORDER BY source.customers.customer_id ASC

SELECT
    source.customers.customer_id as customer_id,
    source.accounts.account_id as account_id
FROM source.customers
LEFT JOIN source.accounts
ON SOURCE.CUSTOMERS.customer_id = SOURCE.accounts.customer_id
WHERE account_id is NULL

select 
    DISTINCT SOURCE.CUSTOMERS.customer_id
FROM SOURCE.customers
left JOIN SOURCE.accounts
ON SOURCE.CUSTOMERS.customer_id = SOURCE.accounts.customer_id
WHERE source.accounts.account_id is NULL


SELECT 
    source.transactions.account_id,
    sum(source.transactions.amount) as total_amount,
    count(source.transactions.amount) as transaction_count
from source.transactions
WHERE
    source.transactions.transaction_time >= '2026-01-01'
    AND source.transactions.transaction_time <'2027-01-01'
GROUP BY source.transactions.account_id
ORDER BY total_amount DESC


SELECT
    source.transactions.account_id,
    sum(source.transactions.amount) as total_amount,
    count(source.transactions.amount) as transaction_count
FROM source.transactions
WHERE source.transactions.transaction_time >= '2026-01-01'
    AND source.transactions.transaction_time < '2027-01-01'
GROUP BY source.transactions.account_id
HAVING sum(source.transactions.amount) > 50000
    AND count(source.transactions.amount) >= 10
ORDER BY total_amount DESC


with total_disbursed as (
    SELECT 
        SOURCE.loan_disbursements.loan_id,
        sum(source.loan_disbursements.disbursement_amount) as total_disbursed
    FROM 
        loan_disbursements
    GROUP BY SOURCE.loan_disbursements.loan_id
)
SELECT 
    *
FROM
    total_disbursed
WHERE total_disbursed.total_disbursed > 100000
ORDER BY total_disbursed.total_disbursed DESC

with total_loan as (
    SELECT 
        source.loan_disbursements.loan_id as loan_id,
        sum(source.loan_disbursements.disbursement_amount) as total_loan_amount
    FROM
        source.loan_disbursements
    WHERE source.loan_disbursements.disbursement_status = 'SUCCESS'
    GROUP BY loan_id
),
    total_repay as (
        SELECT
            source.loan_repayments.loan_id,
            sum(source.loan_repayments.principal_amount) as total_repay_amount
        FROM source.loan_repayments
        WHERE source.loan_repayments.repayment_status = 'SUCCESS'
        GROUP BY source.loan_repayments.loan_id
    )
select  
    SOURCE.loans.loan_id as loan_id,
    total_loan.total_loan_amount as total_disbursed,
    total_repay.total_repay_amount as total_repaid,
    (COALESCE(total_loan.total_loan_amount,0) 
    - 
    COALESCE(total_repay.total_repay_amount,0))  as outstanding_principal
FROM source.loans
left JOIN total_loan
ON SOURCE.loans.loan_id = total_loan.loan_id
left JOIN total_repay
On SOURCE.loans.loan_id = total_repay.loan_id
ORDER BY  outstanding_principal DESC

SELECT
    t.account_id
FROM source.transactions t


with total_transaction_amount as (
    SELECT
        t.account_id,
        sum(t.amount) as total_amount
    FROM source.transactions t
    WHERE t.transaction_time >= '2026-01-01'
        AND t.transaction_time < '2027-01-01'
    GROUP BY t.account_id
)
SELECT 
    a.account_id,
    a.total_amount,
    rank() OVER (
        ORDER BY total_amount DESC
        ) as amount_rank
FROM
    total_transaction_amount a
ORDER BY amount_rank ASC,a.account_id ASC


WITH total_transaction_amount as (
    SELECT
        t.account_id,
        sum(t.amount) as total_amount
    From source.transactions t
    WHERE
        t.transaction_time >='2026-01-01'
        AND t.transaction_time < '2027-01-01'
    GROUP BY t.account_id
),
total_accounts_amount as (
    SELECT
        sa.customer_id,
        sum(tta1.total_amount) as total_customer_amount
    FROM source.accounts sa
    JOIN total_transaction_amount tta1
    ON sa.account_id = tta1.account_id
    GROUP BY sa.customer_id
)
SELECT
    c.*,
    taa.total_customer_amount,
    rank() OVER(
        PARTITION BY c.region
        ORDER BY taa.total_customer_amount DESC
    ) as region_rank
FROM source.customers c
JOIN total_accounts_amount taa
ON c.customer_id = taa.customer_id
ORDER BY c.region,region_rank,c.customer_id


WITH total_month as (
    SELECT
        date_trunc('month',t.transaction_time) as month,
        sum(t.amount) as monthly_amount
    FROM source.transactions t
    WHERE t.transaction_time >= '2026-01-01'
        AND t.transaction_time < '2027-01-01'
    GROUP BY month
)
SELECT
    total_month.*,
    sum(total_month.monthly_amount) OVER(
        ORDER BY month
        ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW 
    ) as cumulative_amount
FROM total_month 
ORDER BY total_month.month

WITH total_transaction_amount as (
    select 
        date_trunc('month',t.transaction_time) as month,
        sum(t.amount) as monthly_amount
    FROM 
        source.transactions t   
    WHERE t.transaction_time >= '2026-01-01'
        AND t.transaction_time < '2027-01-01'
    GROUP BY month
),
transaction_amount_lag as (
    SELECT
        tta.*,
        LAG(tta.monthly_amount,1) OVER(
            ORDER BY tta.month
            ) as previous_amount
    FROM total_transaction_amount tta
)
SELECT
    tal.*,
    ROUND((tal.monthly_amount-NULLIF(tal.previous_amount,0))
        *100/NULLIF(tal.previous_amount,0),
        2) as mom_growth_pct
FROM
    transaction_amount_lag tal
ORDER BY tal.month ASC


SELECT
    *
FROM(
    SELECT
        T.transaction_id,
        COUNT(T.transaction_id) AS join_count
    FROM SOURCE.transactions AS T 
    JOIN source.accounts as a
    on T.account_id = a.account_id
    Join source.customers as c
    on a.customer_id = c.customer_id
    GROUP BY T.transaction_id
) AS duplicate_check
WHERE join_count >1
ORDER BY join_count DESC


SELECT
    date_trunc('month',t.transaction_time) as month,
    count(DISTINCT c.customer_id) as MAC
FROM source.transactions t
join source.accounts a
on t.account_id = a.account_id
join source.customers c
on a.account_id = c.customer_id
WHERE t.transaction_time >= '2026-01-01'
AND t.transaction_time < '2027-01-01'
GROUP BY month



WITH total_loan as (
    SELECT
        ld.loan_id,
        sum(ld.disbursement_amount) as loan_amount
    FROM
        loan_disbursements ld
    WHERE ld.disbursement_status = 'SUCCESS'
        AND ld.disbursement_time < '2027-01-01'
    GROUP BY ld.loan_id
),
total_repay as (
    SELECT
        lr.loan_id,
        sum(lr.principal_amount) as repay_amount
    FROM
        loan_repayments lr
    WHERE lr.repayment_status = 'SUCCESS'
        AND lr.repayment_time < '2027-01-01'
    GROUP BY lr.loan_id
)
SELECT
    tl.loan_id,
    COALESCE(tl.loan_amount,0) - COALESCE(tr.repay_amount,0) as need_repay
FROM total_loan tl
JOIN total_repay tr
on tl.loan_id = tr.loan_id
GROUP BY tl.loan_id
HAVING need_repay > 0

