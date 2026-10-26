-- D08 / PostgreSQL / 与 source 数据字典 V1.1 对齐
CREATE SCHEMA IF NOT EXISTS dwd;

CREATE TABLE IF NOT EXISTS dwd.dwd_transaction_detail(
    transaction_id BIGINT PRIMARY KEY,
    account_id BIGINT NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount NUMERIC(18,2) not NULL check (amount>0),
    transaction_status VARCHAR(20) NOT NULL,
    transaction_time TIMESTAMP NOT NULL,
    transaction_date DATE NOT NULL,
    source_created_at TIMESTAMP NOT NULL,
    ods_id BIGINT NOT NULL,
    source_batch_id VARCHAR(100) NOT NULL,
    ods_load_time TIMESTAMPTZ NOT NULL,
    dw_load_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_dwd_transaction_type
        CHECK(transaction_type IN ('DEPOSIT','WITHHDRAWAL','TRANSFER')),
    CONSTRAINT ck_dwd_transaction_status
        CHECK(transaction_status IN ('PENDING','SUCCESS','FAILED','CANCELLED','REVERSED')),
    CONSTRAINT ck_dwd_transaction_date
        CHECK(transaction_date = (transaction_time AT TIME ZONE 'Asia/Shanghai')::date)
)


CREATE TABLE IF NOT EXISTS dwd.dwd_transaction_detail (
    transaction_id BIGINT PRIMARY KEY,
    account_id BIGINT NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
    transaction_status VARCHAR(20) NOT NULL,
    transaction_time TIMESTAMPTZ NOT NULL,
    -- 按项目统一业务时区 Asia/Shanghai 派生
    transaction_date DATE NOT NULL,
    source_created_at TIMESTAMPTZ NOT NULL,
    ods_id BIGINT NOT NULL,
    source_batch_id VARCHAR(100) NOT NULL,
    ods_load_time TIMESTAMPTZ NOT NULL,
    dw_load_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_dwd_transaction_type
      CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER')),
    CONSTRAINT ck_dwd_transaction_status
      CHECK (transaction_status IN ('PENDING', 'SUCCESS', 'FAILED', 'CANCELLED', 'REVERSED')),
    CONSTRAINT ck_dwd_transaction_date
      CHECK (transaction_date = (transaction_time AT TIME ZONE 'Asia/Shanghai')::date)
);
CREATE INDEX IF NOT EXISTS idx_dwd_transaction_date_status
    ON dwd.dwd_transaction_detail (transaction_date, transaction_status);
CREATE INDEX IF NOT EXISTS idx_dwd_transaction_account_time
    ON dwd.dwd_transaction_detail (account_id, transaction_time);
COMMENT ON TABLE dwd.dwd_transaction_detail IS '交易当前标准明细：一笔 transaction_id 一行（保留 REVERSED）';

CREATE TABLE IF NOT EXISTS dwd.dwd_loan_snapshot (
    loan_id BIGINT NOT NULL,
    snapshot_date DATE NOT NULL,
    customer_id BIGINT NOT NULL,
    contract_date DATE NOT NULL,
    contract_amount NUMERIC(18,2) NOT NULL CHECK (contract_amount > 0),
    total_disbursed NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_disbursed >= 0),
    total_principal_repaid NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_principal_repaid >= 0),
    outstanding_principal NUMERIC(18,2) GENERATED ALWAYS AS
        (total_disbursed - total_principal_repaid) STORED,
    -- 避免把 source.loans 当前状态误当作任意历史日期状态：此处不存 loan_status
    dw_load_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_dwd_loan_snapshot PRIMARY KEY (loan_id, snapshot_date),
    CONSTRAINT ck_dwd_loan_snapshot_date CHECK (snapshot_date >= contract_date),
    CONSTRAINT ck_dwd_loan_snapshot_repay CHECK (total_principal_repaid <= total_disbursed)
);
CREATE INDEX IF NOT EXISTS idx_dwd_loan_snapshot_date
    ON dwd.dwd_loan_snapshot (snapshot_date);
COMMENT ON TABLE dwd.dwd_loan_snapshot IS '截至业务日的贷款本金状态：一笔贷款每个日期一行';
COMMENT ON COLUMN dwd.dwd_loan_snapshot.total_disbursed IS '截至当天成功放款累计，按 Asia/Shanghai 业务日';
COMMENT ON COLUMN dwd.dwd_loan_snapshot.total_principal_repaid IS '截至当天成功归还本金累计，不含利息';
