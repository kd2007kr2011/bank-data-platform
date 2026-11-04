
-- D10：交易最新状态表
-- 一笔业务交易只保留一条最新状态记录。

CREATE SCHEMA IF NOT EXISTS ods;

CREATE TABLE IF NOT EXISTS ods.transaction_current (
    transaction_id BIGINT PRIMARY KEY,
    account_id BIGINT NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount NUMERIC(18,2) NOT NULL,
    transaction_status VARCHAR(20) NOT NULL,
    transaction_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    batch_id BIGINT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transaction_current_updated
ON ods.transaction_current (updated_at);


