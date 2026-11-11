-- ODS 唯一性检查：ods.transaction_current 一笔交易只应保留一条最新状态。
-- 文件：sql/ods/checks/duplicate_check.sql

SELECT
    transaction_id,
    COUNT(*) AS cnt
FROM ods.transaction_current
GROUP BY transaction_id
HAVING COUNT(*) > 1;
