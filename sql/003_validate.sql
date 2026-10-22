
-- =====================================================
-- 文件：sql/source/003_validate.sql
-- 用途：验证零售银行源业务表
-- 数据库：PostgreSQL
-- =====================================================

-- 1. 检查六张表的数据量
SELECT 'customers' AS table_name, COUNT(*) AS row_count
FROM source.customers
UNION ALL
SELECT 'accounts', COUNT(*) FROM source.accounts
UNION ALL
SELECT 'transactions', COUNT(*) FROM source.transactions
UNION ALL
SELECT 'loans', COUNT(*) FROM source.loans
UNION ALL
SELECT 'loan_disbursements', COUNT(*) FROM source.loan_disbursements
UNION ALL
SELECT 'loan_repayments', COUNT(*) FROM source.loan_repayments;


-- 2. 检查账户关联的客户是否存在
SELECT a.*
FROM source.accounts a
LEFT JOIN source.customers c
    ON a.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- 3. 检查交易关联的账户是否存在
SELECT t.*
FROM source.transactions t
LEFT JOIN source.accounts a
    ON t.account_id = a.account_id
WHERE a.account_id IS NULL;


-- 4. 检查贷款关联的客户是否存在
SELECT l.*
FROM source.loans l
LEFT JOIN source.customers c
    ON l.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- 5. 检查放款关联的贷款是否存在
SELECT d.*
FROM source.loan_disbursements d
LEFT JOIN source.loans l
    ON d.loan_id = l.loan_id
WHERE l.loan_id IS NULL;


-- 6. 检查还款关联的贷款是否存在
SELECT r.*
FROM source.loan_repayments r
LEFT JOIN source.loans l
    ON r.loan_id = l.loan_id
WHERE l.loan_id IS NULL;


-- 7. 检查是否存在非法金额
SELECT 'transactions' AS table_name, transaction_id AS record_id
FROM source.transactions
WHERE amount <= 0

UNION ALL

SELECT 'loans', loan_id
FROM source.loans
WHERE contract_amount <= 0

UNION ALL

SELECT 'loan_disbursements', disbursement_id
FROM source.loan_disbursements
WHERE disbursement_amount <= 0

UNION ALL

SELECT 'loan_repayments', repayment_id
FROM source.loan_repayments
WHERE principal_amount < 0
   OR interest_amount < 0
   OR principal_amount + interest_amount <= 0;


-- 8. 统计交易状态分布
SELECT transaction_status,
       COUNT(*) AS transaction_count,
       SUM(amount) AS total_amount
FROM source.transactions
GROUP BY transaction_status
ORDER BY transaction_status;


-- 9. 统计每位客户的账户数量
SELECT c.customer_id,
       c.customer_name,
       COUNT(a.account_id) AS account_count
FROM source.customers c
LEFT JOIN source.accounts a
    ON c.customer_id = a.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY c.customer_id;


-- 10. 计算每笔贷款的剩余本金
SELECT
    l.loan_id,
    l.contract_amount,
    COALESCE(d.total_disbursed, 0) AS total_disbursed,
    COALESCE(r.total_principal_repaid, 0) AS total_principal_repaid,
    COALESCE(d.total_disbursed, 0)
        - COALESCE(r.total_principal_repaid, 0) AS outstanding_principal
FROM source.loans l
LEFT JOIN (
    SELECT loan_id, SUM(disbursement_amount) AS total_disbursed
    FROM source.loan_disbursements
    WHERE disbursement_status = 'SUCCESS'
    GROUP BY loan_id
) d ON l.loan_id = d.loan_id
LEFT JOIN (
    SELECT loan_id, SUM(principal_amount) AS total_principal_repaid
    FROM source.loan_repayments
    WHERE repayment_status = 'SUCCESS'
    GROUP BY loan_id
) r ON l.loan_id = r.loan_id
ORDER BY l.loan_id;
