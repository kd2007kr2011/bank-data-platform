"""D14：贷款快照幂等重跑与历史回补（VS Code 直接运行版）。"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path
from decimal import Decimal

import psycopg
from psycopg import sql
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


# ==========================================
# ⚙️ 配置区域：直接在这里修改你要运行的参数
# ==========================================
RUN_START_DATE = "2026-11-01"   # 开始业务日 (YYYY-MM-DD)
RUN_END_DATE   = "2026-11-03"   # 结束业务日 (如果只跑一天，保持和开始日期相同)
RUN_REASON     = "vscode_direct_run" # 重跑原因
# ==========================================


def get_connection():
    """建立数据库连接。"""
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "bank_dev"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        autocommit=True,
    )


def snapshot_stats(conn, snapshot_date,
                   target_schema, target_table):
    """读取指定日期的快照统计信息。"""

    query = sql.SQL("""
        SELECT
            COUNT(*) AS row_count,
            COALESCE(
                SUM(outstanding_principal), 0
            ) AS total_balance
        FROM {}.{}
        WHERE snapshot_date = %s
    """).format(
        sql.Identifier(target_schema),
        sql.Identifier(target_table),
    )

    with conn.cursor() as cur:
        cur.execute(query, (snapshot_date,))
        count, total = cur.fetchone()

    return int(count), total


def build_snapshot(
    conn,
    snapshot_date,
    source_schema="source",
    target_schema="dwd",
    target_table="loan_snapshot_d14_demo",
    audit_schema="dwd",
    reason="scheduled",
):
    """在一个事务中重建指定日期的完整快照。"""

    if isinstance(snapshot_date, str):
        snapshot_date = date.fromisoformat(
            snapshot_date
        )

    with conn.transaction():

        # ---------- 1. 重跑前统计 ----------
        old_count, old_total = snapshot_stats(
            conn,
            snapshot_date,
            target_schema,
            target_table,
        )

        # ---------- 2. 删除该日期旧快照 ----------
        delete_sql = sql.SQL("""
            DELETE FROM {}.{}
            WHERE snapshot_date = %s
        """).format(
            sql.Identifier(target_schema),
            sql.Identifier(target_table),
        )

        with conn.cursor() as cur:
            cur.execute(
                delete_sql,
                (snapshot_date,),
            )

        # ---------- 3. 重新计算贷款快照 ----------
        insert_sql = sql.SQL("""
            WITH disbursement AS (
                SELECT
                    loan_id,
                    SUM(disbursement_amount)
                        AS total_disbursed
                FROM {}.loan_disbursements
                WHERE disbursement_status = 'SUCCESS'
                  AND disbursement_time <
                      (%s::date + INTERVAL '1 day')
                GROUP BY loan_id
            ),

            repayment AS (
                SELECT
                    loan_id,
                    SUM(principal_amount)
                        AS total_repaid
                FROM {}.loan_repayments
                WHERE repayment_status = 'SUCCESS'
                  AND repayment_time <
                      (%s::date + INTERVAL '1 day')
                GROUP BY loan_id
            )

            INSERT INTO {}.{} (
                snapshot_date,
                loan_id,
                total_disbursed,
                total_repaid,
                outstanding_principal
            )

            SELECT
                %s::date,
                d.loan_id,
                d.total_disbursed,
                COALESCE(r.total_repaid, 0),
                d.total_disbursed
                    - COALESCE(r.total_repaid, 0)

            FROM disbursement d
            LEFT JOIN repayment r
                ON d.loan_id = r.loan_id

        """).format(
            sql.Identifier(source_schema),
            sql.Identifier(source_schema),
            sql.Identifier(target_schema),
            sql.Identifier(target_table),
        )

        with conn.cursor() as cur:
            cur.execute(
                insert_sql,
                (
                    snapshot_date,
                    snapshot_date,
                    snapshot_date,
                ),
            )

        # ---------- 4. 重跑后统计 ----------
        new_count, new_total = snapshot_stats(
            conn,
            snapshot_date,
            target_schema,
            target_table,
        )

        # ---------- 5. 保存重跑日志 ----------
        if audit_schema is not None:

            audit_sql = sql.SQL("""
                INSERT INTO {}.etl_replay_log (
                    snapshot_date,
                    run_reason,
                    old_count,
                    new_count,
                    old_total,
                    new_total
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """).format(
                sql.Identifier(audit_schema)
            )

            with conn.cursor() as cur:
                cur.execute(
                    audit_sql,
                    (
                        snapshot_date,
                        reason,
                        old_count,
                        new_count,
                        old_total,
                        new_total,
                    ),
                )

    return {
        "date": snapshot_date.isoformat(),
        "old_count": old_count,
        "new_count": new_count,
        "old_total": old_total,
        "new_total": new_total,
    }


def backfill(start_date, end_date, reason):
    """按业务日期逐日重新计算快照。"""

    if end_date < start_date:
        raise ValueError("结束日期不能早于开始日期")

    with get_connection() as conn:

        current = start_date

        while current <= end_date:

            result = build_snapshot(
                conn,
                current,
                reason=reason,
            )

            print(
                f"{result['date']} | "
                f"记录数："
                f"{result['old_count']} -> "
                f"{result['new_count']} | "
                f"余额："
                f"{result['old_total']} -> "
                f"{result['new_total']}"
            )

            current += timedelta(days=1)


if __name__ == "__main__":
    # 直接使用上方配置区域的变量，移除 argparse 命令行参数
    start = date.fromisoformat(RUN_START_DATE)
    end = date.fromisoformat(RUN_END_DATE)

    backfill(start, end, RUN_REASON)