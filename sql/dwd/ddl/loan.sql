CREATE SCHEMA IF NOT EXISTS dwd;

CREATE TABLE IF NOT EXISTS dwd.dwd_loan (
    loan_id BIGINT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    contract_amount NUMERIC(18,2) NOT NULL,
    loan_status VARCHAR(20) NOT NULL,
    contract_date DATE NOT NULL,
    source_created_at TIMESTAMPTZ,
    etl_updated_at TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_dwd_loan_amount
        CHECK (contract_amount > 0),

    CONSTRAINT ck_dwd_loan_status
        CHECK (loan_status IN (
            'PENDING',
            'ACTIVE',
            'PAID_OFF',
            'CANCELLED'
        ))
);



CREATE TABLE IF NOT EXISTS dwd.dwd_repayment_event (
    repayment_id BIGINT PRIMARY KEY,
    loan_id BIGINT NOT NULL,
    principal_amount NUMERIC(18,2) NOT NULL,
    interest_amount NUMERIC(18,2) NOT NULL,
    repayment_status VARCHAR(20) NOT NULL,
    repayment_time TIMESTAMPTZ NOT NULL,
    source_created_at TIMESTAMPTZ,
    etl_updated_at TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_repayment_amount
        CHECK (
            principal_amount >= 0
            AND interest_amount >= 0
            AND principal_amount + interest_amount > 0
        ),

    CONSTRAINT ck_repayment_status
        CHECK (repayment_status IN (
            'PENDING',
            'SUCCESS',
            'FAILED',
            'CANCELLED'
        )),

    CONSTRAINT fk_dwd_repayment_loan
        FOREIGN KEY (loan_id)
        REFERENCES dwd.dwd_loan(loan_id)
);


CREATE TABLE IF NOT EXISTS dwd.dwd_loan_snapshot (
    snapshot_date DATE NOT NULL,
    loan_id BIGINT NOT NULL,

    total_disbursed NUMERIC(18,2) NOT NULL,
    total_principal_repaid NUMERIC(18,2) NOT NULL,
    total_interest_paid NUMERIC(18,2) NOT NULL,
    outstanding_principal NUMERIC(18,2) NOT NULL,

    overdue_days INTEGER,
    etl_updated_at TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (snapshot_date, loan_id),

    FOREIGN KEY (loan_id)
        REFERENCES dwd.dwd_loan(loan_id),

    CHECK (outstanding_principal >= 0),
    CHECK (overdue_days IS NULL OR overdue_days >= 0)
);