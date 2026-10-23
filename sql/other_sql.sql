SELECT version();

SELECT current_database();

SELECT current_schema();

-- 约束测试脚本：以下语句均预期失败
-- 执行时请手动逐条运行，确认报错信息与说明一致。
-- 如需实际执行，请先执行 sql/001_schema.sql 并载入数据。


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
