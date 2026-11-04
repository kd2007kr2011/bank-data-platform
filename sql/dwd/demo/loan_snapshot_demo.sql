CREATE TABLE IF NOT EXISTS dwd.loan_snapshot_d14_demo (
    snapshot_date DATE NOT NULL,
    loan_id VARCHAR(30) NOT NULL,

    total_disbursed NUMERIC(18,2) NOT NULL,
    total_repaid NUMERIC(18,2) NOT NULL,
    outstanding_principal NUMERIC(18,2) NOT NULL,

    CONSTRAINT pk_loan_snapshot_d14
        PRIMARY KEY (snapshot_date, loan_id),

    CONSTRAINT ck_loan_balance_d14
        CHECK (outstanding_principal >= 0)
);


CREATE TABLE IF NOT EXISTS dwd.etl_replay_log (
    run_id BIGSERIAL PRIMARY KEY,

    snapshot_date DATE NOT NULL,
    run_reason TEXT NOT NULL,

    old_count INTEGER NOT NULL,
    new_count INTEGER NOT NULL,

    old_total NUMERIC(20,2) NOT NULL,
    new_total NUMERIC(20,2) NOT NULL,

    executed_at TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP
);

