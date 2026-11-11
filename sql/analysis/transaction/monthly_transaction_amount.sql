-- 月度交易金额统计：按月汇总交易笔数与金额，观察交易规模趋势。
-- 文件：sql/analysis/transaction/monthly_transaction_amount.sql

-- 1. 指定年份的头两个月（示例：2026 年 1-2 月）
SELECT
    date_trunc('month', transaction_time) AS month,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount
FROM source.transactions
WHERE EXTRACT(YEAR FROM transaction_time) = 2026
  AND EXTRACT(MONTH FROM transaction_time) IN (1, 2)
GROUP BY date_trunc('month', transaction_time)
ORDER BY month;

-- 2. 全量年份：按月汇总，并按金额从高到低排序
SELECT
    date_trunc('month', transaction_time) AS month,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount
FROM source.transactions
GROUP BY date_trunc('month', transaction_time)
ORDER BY total_amount DESC;
