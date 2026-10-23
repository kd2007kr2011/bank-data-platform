# 数据说明

本目录原用于存放项目数据说明，实际生成的合成数据位于 `scripts/data/generated/`（本地生成，不纳入版本控制）。

完整的项目介绍、数据规模和数据生成规则见项目根目录的 [README.md](../README.md)。

## 数据来源

所有业务数据均由 `scripts/generate/generate.py` 程序生成，用于模拟零售银行的客户、账户、交易、贷款、放款和还款记录，**不包含任何真实银行客户信息、账户流水或贷款记录**。

## 生成的数据文件

| 文件 | 说明 |
|---|---|
| `customers.csv` | 客户信息，1,000 行 |
| `accounts.csv` | 账户信息，2,057 行 |
| `transactions.csv` | 交易流水，15,467 行 |
| `loans.csv` | 贷款合同，286 行 |
| `loan_disbursements.csv` | 实际放款，286 行 |
| `loan_repayments.csv` | 贷款还款，286 行 |
| `validation_report.txt` | `validate.py` 输出的数据质量校验报告 |

业务日期覆盖 2022-01-06 至 2026-10-22，最近一次校验结果：`PASS`，错误数 `0`。

## 重新生成

生成参数见 `scripts/config/generator.yaml`，包括随机种子、日期范围、客户数、账户与交易数量、贷款概率等。

```bash
python scripts/generate/generate.py    # 生成 CSV
python scripts/generate/validate.py    # 校验 CSV
python scripts/generate/load_to_db.py  # 导入 PostgreSQL 的 source schema
```

使用固定随机种子，相同的配置可以复现完全相同的数据。

## 使用原则

1. 不导入真实银行客户信息、账户流水或真实贷款记录。
2. 不在仓库中提交数据库密码、访问令牌或其他敏感凭据。
3. 合成数据中的金额、客户状态及业务事件仅用于功能演示，不代表真实银行业务分布。
4. 如后续引用公开数据集，将单独记录数据来源、许可条件及使用范围。
