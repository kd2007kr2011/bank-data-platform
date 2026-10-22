SELECT version();

SELECT current_database();

SELECT current_schema();

INSERT INTO source.loan_repayments
    (repayment_id, loan_id, repayment_amount)
VALUES
    (990003, 888888, 500.00);