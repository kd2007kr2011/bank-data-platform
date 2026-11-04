BEGIN;

INSERT INTO source.customers
    (customer_id,customer_name,customer_type,customer_status,open_date)
VALUES
    (1,'模拟客户001','INDIVIDUAL','ACTIVE','2025-01-10'),
    (2,'模拟客户002','INDIVIDUAL','ACTIVE','2025-02-15'),
    (3,'模拟企业001','BUSINESS','INACTIVE','2025-03-01');

-- 2. 账户数据
INSERT INTO source.accounts
    (account_id, customer_id, account_type, account_status, open_date)
VALUES
    (101, 1, 'SAVINGS', 'ACTIVE', '2025-01-10'),
    (102, 1, 'CURRENT', 'ACTIVE', '2025-02-01'),
    (103, 2, 'SAVINGS', 'ACTIVE', '2025-02-15'),
    (104, 3, 'CURRENT', 'CLOSED', '2025-03-01');

-- 3. 交易数据
INSERT INTO source.transactions
    (transaction_id, account_id, transaction_type, amount,
     transaction_status, transaction_time)
VALUES
    (1001, 101, 'DEPOSIT',    5000.00, 'SUCCESS',   '2025-04-01 09:00:00+08'),
    (1002, 101, 'WITHDRAWAL',  800.00, 'SUCCESS',   '2025-04-01 10:00:00+08'),
    (1003, 102, 'TRANSFER',   1200.00, 'FAILED',    '2025-04-02 11:00:00+08'),
    (1004, 103, 'DEPOSIT',    3000.00, 'SUCCESS',   '2025-04-02 12:00:00+08'),
    (1005, 101, 'TRANSFER',    200.00, 'CANCELLED', '2025-04-03 13:00:00+08');

-- 4. 贷款合同数据
INSERT INTO source.loans
    (loan_id, customer_id, contract_amount, loan_status, contract_date)
VALUES
    (501, 1, 100000.00, 'ACTIVE', '2025-01-20'),
    (502, 2,  50000.00, 'ACTIVE', '2025-02-20');

-- 5. 实际放款数据
INSERT INTO source.loan_disbursements
    (disbursement_id, loan_id, disbursement_amount,
     disbursement_status, disbursement_time)
VALUES
    (6001, 501, 60000.00, 'SUCCESS', '2025-01-21 10:00:00+08'),
    (6002, 501, 20000.00, 'SUCCESS', '2025-02-01 10:00:00+08'),
    (6003, 502, 50000.00, 'SUCCESS', '2025-02-21 10:00:00+08');

-- 6. 还款数据
INSERT INTO source.loan_repayments
    (repayment_id, loan_id, principal_amount, interest_amount,
     repayment_status, repayment_time)
VALUES
    (7001, 501, 10000.00, 500.00, 'SUCCESS', '2025-03-01 10:00:00+08'),
    (7002, 501,  5000.00, 400.00, 'SUCCESS', '2025-04-01 10:00:00+08'),
    (7003, 502,     0.00, 300.00, 'SUCCESS', '2025-04-02 10:00:00+08');

COMMIT;