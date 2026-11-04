-- 创建各数据层的 schema（可重复执行）。
CREATE SCHEMA IF NOT EXISTS source;
CREATE SCHEMA IF NOT EXISTS ods;
CREATE SCHEMA IF NOT EXISTS dwd;
CREATE SCHEMA IF NOT EXISTS dws;
CREATE SCHEMA IF NOT EXISTS ads;

-- 核对已创建的 schema
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('source', 'ods', 'dwd', 'dws', 'ads')
ORDER BY schema_name;

SELECT current_database();
