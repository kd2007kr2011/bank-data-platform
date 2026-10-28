CREATE OR REPLACE FUNCTION source.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_transactions_updated_at
BEFORE UPDATE ON source.transactions
FOR EACH ROW
EXECUTE FUNCTION source.set_updated_at();

UPDATE source.transactions
SET transaction_status = 'SUCCESS'
WHERE transaction_id = 1001;

UPDATE source.transactions
SET transaction_status = 'SUCCESS'
WHERE transaction_id = 9999

UPDATE source.transactions
SET
 transaction_status = 'SUCCESS'
WHERE
    transaction_id = 2000