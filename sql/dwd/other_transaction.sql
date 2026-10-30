SELECT
    transaction_type,
    COUNT(*) AS cnt
FROM ods.transaction_current
GROUP BY transaction_type
ORDER BY cnt DESC;