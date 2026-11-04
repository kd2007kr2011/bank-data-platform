ALTER TABLE source.customers
ADD COLUMN IF NOT EXISTS region VARCHAR(50);

UPDATE source.customers
SET region = (
    ARRAY[
        '广东',
        '北京',
        '上海',
        '浙江',
        '江苏',
        '四川',
        '湖北',
        '福建'
    ]
)[FLOOR(RANDOM() * 8)::INT + 1]
WHERE region IS NULL;

SELECT
    region,
    COUNT(*) AS customer_count
FROM source.customers
GROUP BY region
ORDER BY customer_count DESC;


SELECT COUNT(*) AS missing_region_count
FROM source.customers
WHERE region IS NULL;