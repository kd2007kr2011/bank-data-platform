-- 大额高频账户：年度交易金额超过 5 万元且交易笔数不少于 10 笔的账户。
-- 文件：sql/analysis/account/high_value_accounts.sql

SELECT
    source.transactions.account_id,
    SUM(source.transactions.amount) AS total_amount,
    COUNT(source.transactions.amount) AS transaction_count
FROM source.transactions
WHERE source.transactions.transaction_time >= '2026-01-01'
  AND source.transactions.transaction_time <  '2027-01-01'
GROUP BY source.transactions.account_id
HAVING SUM(source.transactions.amount) > 50000
   AND COUNT(source.transactions.amount) >= 10
ORDER BY total_amount DESC;
