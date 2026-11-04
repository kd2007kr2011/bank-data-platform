-- 约束失败用例：以下语句均预期报错，需逐条手动执行并确认报错信息。
-- 执行前请先建表并载入数据：
--   psql -U postgres -d bank_dev -f sql/source/ddl/001_schema.sql


-- 测试 1：不存在的客户，预期触发外键错误
INSERT INTO source.accounts
    (customer_id, account_type, open_date)
VALUES
    (999999, 'SAVINGS', CURRENT_DATE);


-- 测试 2：重复的交易编号，预期触发主键错误
INSERT INTO source.transactions
    (transaction_id, account_id, transaction_type,
     amount, transaction_status, transaction_time)
VALUES
    (1, 1, 'DEPOSIT', 100.00, 'SUCCESS', CURRENT_TIMESTAMP);


-- 测试 3：负本金，预期触发 CHECK 约束错误
INSERT INTO source.loan_repayments
    (loan_id, principal_amount, interest_amount,
     repayment_status, repayment_time)
VALUES
    (1, -100.00, 10.00, 'SUCCESS', CURRENT_TIMESTAMP);
