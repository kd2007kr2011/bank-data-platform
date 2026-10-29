
"""ODS 数据质量规则：检查交易数据并隔离异常记录。"""

from collections import defaultdict
from datetime import datetime

import pandas as pd


def check_transaction_quality(records, valid_account_ids):
    """
    检查交易数据质量。

    参数
    ----
    records:
        list[dict]，每个 dict 代表一条交易记录。

    valid_account_ids:
        set，当前有效账户 ID 集合。

    返回
    ----
    valid_records:
        通过质量检查的记录。

    rejected_records:
        拒收记录，每条包含原始数据、规则编码和原因。
    """

    rejected_records = []
    valid_records = []

    # 第一轮：统计同一交易 ID 出现了多少次
    id_records = defaultdict(list)

    for record in records:
        transaction_id = record.get("transaction_id")

        if transaction_id is not None and str(transaction_id).strip():
            id_records[str(transaction_id)].append(record)

    # 找出同一 ID 对应不同业务内容的冲突
    conflict_ids = set()

    for transaction_id, group in id_records.items():
        # 比较除 transaction_id 外的全部字段
        contents = {
            tuple(sorted(
                (key, str(value))
                for key, value in record.items()
                if key != "transaction_id"
            ))
            for record in group
        }

        if len(contents) > 1:
            conflict_ids.add(transaction_id)

    # 第二轮：逐条执行质量规则
    for record in records:
        reasons = []
        transaction_id = record.get("transaction_id")
        account_id = record.get("account_id")
        transaction_time = record.get("transaction_time")

        # 规则 1：交易 ID 非空
        if transaction_id is None or not str(transaction_id).strip():
            reasons.append((
                "NULL_TRANSACTION_ID",
                "transaction_id 不能为空"
            ))

        # 规则 2：账户必须存在
        elif account_id is None or account_id not in valid_account_ids:
            reasons.append((
                "INVALID_ACCOUNT",
                f"账户不存在或为空：{account_id}"
            ))

        # 规则 3：交易时间必须合法
        if transaction_time is None:
            reasons.append((
                "INVALID_TRANSACTION_TIME",
                "transaction_time 不能为空"
            ))
        else:
            try:
                parsed_time = pd.to_datetime(
                    transaction_time,
                    errors="raise"
                )

                if pd.isna(parsed_time):
                    raise ValueError("时间为空")

            except (ValueError, TypeError, OverflowError):
                reasons.append((
                    "INVALID_TRANSACTION_TIME",
                    f"交易时间格式错误：{transaction_time}"
                ))

        # 规则 4：同一交易 ID 存在内容冲突
        if (
            transaction_id is not None
            and str(transaction_id).strip()
            and str(transaction_id) in conflict_ids
        ):
            reasons.append((
                "DUPLICATE_TRANSACTION_ID",
                f"交易 ID 对应多条不同内容的记录：{transaction_id}"
            ))

        # 一条记录可以同时违反多条规则
        if reasons:
            for rule_code, reason in reasons:
                rejected_records.append({
                    "raw_data": record.copy(),
                    "rule_code": rule_code,
                    "reject_reason": reason,
                })
        else:
            valid_records.append(record.copy())

    return valid_records, rejected_records
