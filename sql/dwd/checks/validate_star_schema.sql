
-- ============================================================
-- D15 星型模型验证
--
-- 文件：sql/dwd/checks/validate_star_schema.sql
-- 数据库：bank_dev
-- ============================================================

-- 1. 检查五张表的数据量
SELECT 'dim_region' AS table_name, COUNT(*) AS row_count
FROM dwd.dim_region

UNION ALL

SELECT 'dim_customer', COUNT(*)
FROM dwd.dim_customer

UNION ALL

SELECT 'dim_date', COUNT(*)
FROM dwd.dim_date

UNION ALL

SELECT 'fact_transaction', COUNT(*)
FROM dwd.fact_transaction

UNION ALL

SELECT 'fact_loan_daily', COUNT(*)
FROM dwd.fact_loan_daily;


-- ============================================================
-- 2. 交易事实业务键检查
-- 预期结果：0
-- ============================================================

SELECT COUNT(*) AS duplicate_transaction_count
FROM (
    SELECT transaction_id
    FROM dwd.fact_transaction
    GROUP BY transaction_id
    HAVING COUNT(*) > 1
) AS t;


-- ============================================================
-- 3. 贷款日快照粒度检查
-- 预期结果：0
-- ============================================================

SELECT COUNT(*) AS duplicate_loan_daily_count
FROM (
    SELECT loan_id, date_key
    FROM dwd.fact_loan_daily
    GROUP BY loan_id, date_key
    HAVING COUNT(*) > 1
) AS t;


-- ============================================================
-- 4. 客户维度关联完整性
-- 预期结果：0
-- ============================================================

SELECT COUNT(*) AS missing_customer_count
FROM dwd.fact_transaction AS f

LEFT JOIN dwd.dim_customer AS c
    ON f.customer_key = c.customer_key

WHERE c.customer_key IS NULL;


-- ============================================================
-- 5. 查询各地区交易金额
-- ============================================================

SELECT
    r.region_name,

    COUNT(*) AS transaction_count,

    SUM(f.amount) AS total_amount

FROM dwd.fact_transaction AS f

JOIN dwd.dim_region AS r
    ON f.region_key = r.region_key

WHERE f.transaction_status = 'SUCCESS'

GROUP BY r.region_name

ORDER BY total_amount DESC;


-- ============================================================
-- 6. 查询每天的贷款余额
-- ============================================================

SELECT
    d.full_date,

    COUNT(*) AS loan_count,

    SUM(
        f.outstanding_principal
    ) AS total_outstanding

FROM dwd.fact_loan_daily AS f

JOIN dwd.dim_date AS d
    ON f.date_key = d.date_key

GROUP BY d.full_date

ORDER BY d.full_date;


-- ============================================================
-- 7. 检查维度关联是否增加行数
-- 预期结果：两列相同
-- ============================================================

SELECT

    (
        SELECT COUNT(*)
        FROM dwd.fact_transaction
    ) AS original_rows,

    (
        SELECT COUNT(*)
        FROM dwd.fact_transaction AS f

        JOIN dwd.dim_customer AS c
            ON f.customer_key = c.customer_key

        JOIN dwd.dim_date AS d
            ON f.date_key = d.date_key

    ) AS joined_rows;


-- ============================================================
-- 8. 检查事实表金额平衡
-- ============================================================

SELECT

    COUNT(*) AS transaction_count,

    COALESCE(
        SUM(amount), 0
    ) AS original_amount,

    (
        SELECT COALESCE(
            SUM(f.amount), 0
        )
        FROM dwd.fact_transaction AS f

        JOIN dwd.dim_customer AS c
            ON f.customer_key = c.customer_key

        JOIN dwd.dim_date AS d
            ON f.date_key = d.date_key

    ) AS joined_amount

FROM dwd.fact_transaction;


-- ============================================================
-- 9. 查询某一天各地区的贷款余额
-- ============================================================

SELECT
    d.full_date,

    r.region_name,

    COUNT(*) AS loan_count,

    SUM(
        f.outstanding_principal
    ) AS outstanding_balance

FROM dwd.fact_loan_daily AS f

JOIN dwd.dim_date AS d
    ON f.date_key = d.date_key

JOIN dwd.dim_region AS r
    ON f.region_key = r.region_key

GROUP BY
    d.full_date,
    r.region_name

ORDER BY
    d.full_date DESC,
    outstanding_balance DESC;


-- ============================================================
-- 10. 检查贷款余额计算一致性
-- 仅适用于本金还款口径
-- 预期结果：0
-- ============================================================

SELECT COUNT(*) AS inconsistent_loan_count

FROM dwd.fact_loan_daily

WHERE outstanding_principal
    <> GREATEST(
        total_disbursed - total_repaid_principal,
        0
    );
