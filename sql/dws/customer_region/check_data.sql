SELECT
    (
        SELECT SUM(total_transaction_count)
        FROM dws.dws_customer_transaction_daily
    ) AS customer_total_count,

    (
        SELECT SUM(total_transaction_count)
        FROM dws.dws_region_transaction_daily
    ) AS region_total_count,

    (
        SELECT COUNT(*)
        FROM dwd.fact_transaction
    ) AS dwd_total_count;