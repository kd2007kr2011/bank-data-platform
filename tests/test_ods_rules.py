
"""ODS 数据质量规则单元测试。"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from etl.quality.ods_rules import check_transaction_quality


VALID_ACCOUNTS = {"A001", "A002", "A003"}

# 正常 2 条；异常 4 条（ID 为空、账户不存在、时间非法、ID 内容冲突）
RECORDS = [
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


class TestOdsQualityRules(unittest.TestCase):

    def setUp(self):
        self.valid, self.rejected = check_transaction_quality(
            RECORDS,
            VALID_ACCOUNTS,
        )

    def rule_codes(self):
        return sorted(item["rule_code"] for item in self.rejected)

    def test_01_valid_records(self):
        """只有完全合规的一条记录通过。"""

        self.assertEqual(len(self.valid), 1)
        self.assertEqual(
            [record["transaction_id"] for record in self.valid],
            ["T001"],
        )

    def test_02_rejected_records(self):
        """五条异常记录全部被拒收（含 T005 冲突的两条）。"""

        self.assertEqual(len(self.rejected), 5)

    def test_03_rule_codes(self):
        """四类规则各命中一次。"""

        self.assertEqual(
            self.rule_codes(),
            [
                "DUPLICATE_TRANSACTION_ID",
                "DUPLICATE_TRANSACTION_ID",
                "INVALID_ACCOUNT",
                "INVALID_TRANSACTION_TIME",
                "NULL_TRANSACTION_ID",
            ],
        )

    def test_04_reject_detail(self):
        """拒收明细包含原始数据、规则编码和原因。"""

        for item in self.rejected:
            self.assertIn("raw_data", item)
            self.assertIn("rule_code", item)
            self.assertIn("reject_reason", item)
            self.assertTrue(item["reject_reason"])

    def test_05_valid_records_are_copies(self):
        """返回的是副本，修改不会污染输入。"""

        self.valid[0]["amount"] = -1

        self.assertEqual(RECORDS[0]["amount"], 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
