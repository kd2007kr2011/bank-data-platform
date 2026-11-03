SELECT
    transaction_type,
    COUNT(*) AS cnt
FROM ods.transaction_current
GROUP BY transaction_type
ORDER BY cnt DESC;

SELECT
    transaction_id,
    transaction_type,
    COUNT(*) OVER (
        PARTITION BY transaction_type
    ) AS type_count
FROM ods.transaction_current
WHERE transaction_type IS NULL
   OR transaction_type NOT IN (
       'DEPOSIT',
       'WITHDRAWAL',
       'TRANSFER'
   );

   SELECT
    transaction_type,
    quote_literal(transaction_type) AS raw_value,
    LENGTH(transaction_type) AS char_length,
    OCTET_LENGTH(transaction_type) AS byte_length,
    encode(
        convert_to(transaction_type, 'UTF8'),
        'hex'
    ) AS hex_value,
    COUNT(*) AS cnt
FROM ods.transaction_current
GROUP BY transaction_type
ORDER BY transaction_type;


SELECT
    conname,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'dwd.dwd_transaction_detail'::regclass
  AND conname = 'ck_dwd_transaction_type';

  SELECT
    transaction_type,
    COUNT(*) AS cnt
FROM dwd.dwd_transaction_detail
GROUP BY transaction_type;

SELECT
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'dwd'
  AND table_name = 'dwd_transaction_detail'
  AND column_name = 'transaction_type';


SELECT
    pg_get_constraintdef(oid, true) AS full_definition
FROM pg_constraint
WHERE conrelid = 'dwd.dwd_transaction_detail'::regclass
  AND conname = 'ck_dwd_transaction_type';

  SELECT
    x.transaction_type,
    x.transaction_type IN (
        SELECT unnest(ARRAY[
            'DEPOSIT',
            'WITHDRAWAL',
            'TRANSFER'
        ])
    ) AS is_valid
FROM (
    VALUES
        ('DEPOSIT'),
        ('WITHDRAWAL'),
        ('TRANSFER')
) AS x(transaction_type);

SELECT
    conname,
    pg_get_constraintdef(oid, true) AS full_definition
FROM pg_constraint
WHERE conrelid = 'dwd.dwd_transaction_detail'::regclass;