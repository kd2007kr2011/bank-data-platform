-- 交易表变更时间触发器：每次 UPDATE 自动刷新 updated_at（可重复执行）。

CREATE OR REPLACE FUNCTION source.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_transactions_updated_at ON source.transactions;

CREATE TRIGGER trg_transactions_updated_at
BEFORE UPDATE ON source.transactions
FOR EACH ROW
EXECUTE FUNCTION source.set_updated_at();
