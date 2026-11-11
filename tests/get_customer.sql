

SELECT
    table_schema,
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'dwd'
  AND table_name IN (
      'dwd_loan',
      'dwd_repayment_event',
      'fact_loan_daily'
  )
ORDER BY table_name, ordinal_position;