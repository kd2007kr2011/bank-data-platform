EXPLAIN
SELECT
    *
FROM SOURCE.transactions T
WHERE T.account_id = '55'

EXPLAIN ANALYSE
SELECT
    *
FROM
    source.transactions t
where t.account_id = '66'