-- 执行计划分析：用 EXPLAIN / EXPLAIN ANALYSE 查看查询的索引与扫描方式。

-- 1. 规划阶段：查看可能的索引扫描路径
EXPLAIN
SELECT *
FROM source.transactions AS t
WHERE t.account_id = '55';

-- 2. 分析阶段：实际执行并返回各节点耗时
EXPLAIN ANALYSE
SELECT *
FROM source.transactions AS t
WHERE t.account_id = '66';
