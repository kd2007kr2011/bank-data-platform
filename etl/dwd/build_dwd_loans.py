
"""构建贷款合同和还款事件 DWD。"""

import sys
from pathlib import Path

# 项目根目录：etl/dwd/build_dwd_loans.py -> etl/dwd -> etl -> 项目根
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl.common.db import get_connection


def build_loans(conn):
    """将贷款合同规范化写入 DWD。"""

    sql = """
        INSERT INTO dwd.dwd_loan (
            loan_id,
            customer_id,
            contract_amount,
            loan_status,
            contract_date,
            source_created_at
        )
        SELECT
            loan_id,
            customer_id,
            contract_amount,
            loan_status,
            contract_date,
            created_at
        FROM source.loans
        ON CONFLICT (loan_id)
        DO UPDATE SET
            customer_id = EXCLUDED.customer_id,
            contract_amount = EXCLUDED.contract_amount,
            loan_status = EXCLUDED.loan_status,
            contract_date = EXCLUDED.contract_date,
            source_created_at = EXCLUDED.source_created_at,
            etl_updated_at = CURRENT_TIMESTAMP
        WHERE (
            dwd.dwd_loan.customer_id,
            dwd.dwd_loan.contract_amount,
            dwd.dwd_loan.loan_status,
            dwd.dwd_loan.contract_date,
            dwd.dwd_loan.source_created_at
        ) IS DISTINCT FROM (
            EXCLUDED.customer_id,
            EXCLUDED.contract_amount,
            EXCLUDED.loan_status,
            EXCLUDED.contract_date,
            EXCLUDED.source_created_at
        );
    """

    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.rowcount


def build_repayments(conn):
    """将逐笔还款事件规范化写入 DWD。"""

    sql = """
        INSERT INTO dwd.dwd_repayment_event (
            repayment_id,
            loan_id,
            principal_amount,
            interest_amount,
            repayment_status,
            repayment_time,
            source_created_at
        )
        SELECT
            repayment_id,
            loan_id,
            principal_amount,
            interest_amount,
            repayment_status,
            repayment_time,
            created_at
        FROM source.loan_repayments
        ON CONFLICT (repayment_id)
        DO UPDATE SET
            loan_id = EXCLUDED.loan_id,
            principal_amount = EXCLUDED.principal_amount,
            interest_amount = EXCLUDED.interest_amount,
            repayment_status = EXCLUDED.repayment_status,
            repayment_time = EXCLUDED.repayment_time,
            source_created_at = EXCLUDED.source_created_at,
            etl_updated_at = CURRENT_TIMESTAMP
        WHERE (
            dwd.dwd_repayment_event.loan_id,
            dwd.dwd_repayment_event.principal_amount,
            dwd.dwd_repayment_event.interest_amount,
            dwd.dwd_repayment_event.repayment_status,
            dwd.dwd_repayment_event.repayment_time,
            dwd.dwd_repayment_event.source_created_at
        ) IS DISTINCT FROM (
            EXCLUDED.loan_id,
            EXCLUDED.principal_amount,
            EXCLUDED.interest_amount,
            EXCLUDED.repayment_status,
            EXCLUDED.repayment_time,
            EXCLUDED.source_created_at
        );
    """

    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.rowcount


def main():
    with get_connection() as conn:
        with conn.transaction():
            loan_changed = build_loans(conn)
            repayment_changed = build_repayments(conn)

        print("贷款 DWD 构建成功")
        print(f"贷款合同新增/变更：{loan_changed}")
        print(f"还款事件新增/变更：{repayment_changed}")

if __name__ == "__main__":
    main()
