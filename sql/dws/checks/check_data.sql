
-- ============================================================
-- D17/D18 DWS 汇总结果核对
--
-- 文件：sql/dws/checks/check_data.sql
-- 数据库：bank_dev
--
-- 核对内容：
-- 1. 客户日汇总的交易总笔数
-- 2. 地区日汇总的交易总笔数
-- 3. DWD 交易事实表的行数
--
-- 三者应一致：客户和地区是同一批交易的不同聚合维度。
-- ============================================================

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