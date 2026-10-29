
"""ODS 数据质量规则测试入口。"""

from ods_rules import check_transaction_quality


def main():
    # 模拟正常账户
    valid_accounts = {"A001", "A002", "A003"}

    # 构造正常数据和四类异常数据
    records = [
        {
            "transaction_id": "T001",
            "account_id": "A001",
            "transaction_time": "2026-10-29 09:00:00",
            "amount": 100,
        },
        {
            "transaction_id": None,
            "account_id": "A001",
            "transaction_time": "2026-10-29 09:01:00",
            "amount": 200,
        },
        {
            "transaction_id": "T003",
            "account_id": "A999",
            "transaction_time": "2026-10-29 09:02:00",
            "amount": 300,
        },
        {
            "transaction_id": "T004",
            "account_id": "A002",
            "transaction_time": "not-a-date",
            "amount": 400,
        },
        {
            "transaction_id": "T005",
            "account_id": "A001",
            "transaction_time": "2026-10-29 09:03:00",
            "amount": 500,
        },
        {
            "transaction_id": "T005",
            "account_id": "A001",
            "transaction_time": "2026-10-29 09:03:00",
            "amount": 800,
        },
    ]

    valid, rejected = check_transaction_quality(
        records,
        valid_accounts,
    )

    print("=" * 60)
    print("ODS 数据质量检查结果")
    print("=" * 60)

    print(f"输入记录数：{len(records)}")
    print(f"通过记录数：{len(valid)}")
    print(f"拒收明细数：{len(rejected)}")

    print("\n拒收明细：")

    for item in rejected:
        print(
            f"交易ID={item['raw_data'].get('transaction_id')} | "
            f"规则={item['rule_code']} | "
            f"原因={item['reject_reason']}"
        )

    print("\n通过检查的记录：")

    for record in valid:
        print(record)

    # 统计各规则的拒收数量
    print("\n各规则拒收数量：")

    rule_counts = {}

    for item in rejected:
        code = item["rule_code"]
        rule_counts[code] = rule_counts.get(code, 0) + 1

    for code, count in sorted(rule_counts.items()):
        print(f"{code}: {count}")


if __name__ == "__main__":
    main()
