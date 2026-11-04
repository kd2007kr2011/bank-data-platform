
CREATE SCHEMA IF NOT EXISTS ods;

CREATE TABLE IF NOT EXISTS ods.rejected_records (
    reject_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_table VARCHAR(100) NOT NULL,
    batch_id VARCHAR(100) NOT NULL,
    source_record_key VARCHAR(200),
    raw_data JSONB NOT NULL,
    rule_code VARCHAR(100) NOT NULL,
    reject_reason TEXT NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_rejected_record_rule
        UNIQUE (source_table, record_hash, rule_code)
);
