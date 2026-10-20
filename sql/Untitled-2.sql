-- Active: 1792467033067@@127.0.0.1@5432@bank_dev
CREATE SCHEMA source;
CREATE SCHEMA ods;
CREATE SCHEMA dwd;
CREATE SCHEMA dws;
CREATE SCHEMA ads;

SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('source', 'ods', 'dwd', 'dws', 'ads')
ORDER BY schema_name;

SELECT current_database();


CREATE SCHEMA source;
CREATE SCHEMA ods;
CREATE SCHEMA dwd;
CREATE SCHEMA dws;
CREATE SCHEMA ads;