-- 账户维度的年度交易汇总：每个账户在一年内的交易笔数与总金额。

SELECT
    source.transactions.account_id,
    COUNT(source.transactions.amount) AS transaction_count,
    SUM(source.transactions.amount) AS total_amount
FROM source.transactions
WHERE source.transactions.transaction_time >= '2026-01-01'
  AND source.transactions.transaction_time <  '2027-01-01'
GROUP BY source.transactions.account_id
ORDER BY total_amount DESC;
