
CREATE SCHEMA IF NOT EXISTS ods;

CREATE TABLE IF NOT EXISTS ods.rejected_records (
    reject_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- 来源信息
    source_table VARCHAR(100) NOT NULL,
    batch_id VARCHAR(100) NOT NULL,
    source_record_key VARCHAR(200),

    -- 被拒收的完整原始数据
    raw_data JSONB NOT NULL,

    -- 拒收规则
    rule_code VARCHAR(100) NOT NULL,
    reject_reason TEXT NOT NULL,

    -- 用于重复执行时去重
    record_hash VARCHAR(64) NOT NULL,

    -- 拒收时间
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 同一条原始数据违反同一规则，只记录一次
    CONSTRAINT uq_rejected_record_rule
        UNIQUE (source_table, record_hash, rule_code)
);
