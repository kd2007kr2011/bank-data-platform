# Source 层表结构字典

> 依据：`sql/source/ddl/001_schema.sql`、`sql/source/alter/*.sql` 和 `sql/source/trigger/*.sql`；更新日期：2026-11-10。本文展示执行增量变更后的最终结构。

## 表清单

| 表名 | 中文名称 | 数据粒度 | 主键 |
|---|---|---|---|
| `source.customers` | 客户表 | 一个客户一行 | `customer_id` |
| `source.accounts` | 账户表 | 一个账户一行 | `account_id` |
| `source.transactions` | 交易流水表 | 一笔交易一行 | `transaction_id` |
| `source.loans` | 贷款合同表 | 一笔贷款合同一行 | `loan_id` |
| `source.loan_disbursements` | 贷款放款表 | 一笔放款事件一行 | `disbursement_id` |
| `source.loan_repayments` | 贷款还款表 | 一笔还款事件一行 | `repayment_id` |

## `source.customers`

客户主数据。一名客户可以拥有多个账户和多笔贷款。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `customer_id` | `BIGINT` | 否 | Identity，PK | 客户唯一标识 |
| `customer_name` | `VARCHAR(100)` | 否 |  | 客户姓名或企业名称 |
| `customer_type` | `VARCHAR(20)` | 否 | `INDIVIDUAL/BUSINESS` | 客户类型：个人或企业 |
| `customer_status` | `VARCHAR(20)` | 否 | 默认 `ACTIVE`；`ACTIVE/INACTIVE/CLOSED` | 客户当前状态 |
| `open_date` | `DATE` | 否 |  | 客户开户日期 |
| `created_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 记录创建时间 |
| `region` | `VARCHAR(50)` | 是 | 由 `004_add_customer_region.sql` 添加 | 客户所属地区 |

> `region` 的变更脚本会为已有空值随机填充广东、北京、上海、浙江、江苏、四川、湖北或福建，但字段本身仍允许为空。

## `source.accounts`

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `account_id` | `BIGINT` | 否 | Identity，PK | 账户唯一标识 |
| `customer_id` | `BIGINT` | 否 | FK → `customers.customer_id`，删除受限 | 账户所属客户 |
| `account_type` | `VARCHAR(20)` | 否 | `SAVINGS/CURRENT/CREDIT` | 储蓄、活期或信用账户 |
| `account_status` | `VARCHAR(20)` | 否 | 默认 `ACTIVE`；`ACTIVE/FROZEN/CLOSED` | 账户当前状态 |
| `open_date` | `DATE` | 否 |  | 账户开户日期 |
| `created_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 记录创建时间 |

索引：`(customer_id)`。

## `source.transactions`

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `transaction_id` | `BIGINT` | 否 | Identity，PK | 交易唯一标识 |
| `account_id` | `BIGINT` | 否 | FK → `accounts.account_id`，删除受限 | 交易所属账户 |
| `transaction_type` | `VARCHAR(20)` | 否 | `DEPOSIT/WITHDRAWAL/TRANSFER` | 存款、取款或转账 |
| `amount` | `NUMERIC(18,2)` | 否 | `> 0` | 交易金额 |
| `transaction_status` | `VARCHAR(20)` | 否 | `PENDING/SUCCESS/FAILED/CANCELLED/REVERSED` | 交易状态 |
| `transaction_time` | `TIMESTAMPTZ` | 否 |  | 交易业务发生时间 |
| `created_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 记录创建时间 |
| `updated_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP`；由 D10 变更添加 | 记录最后更新时间，用于增量抽取 |

索引：`(account_id, transaction_time)`、`(transaction_status, transaction_time)`。

触发器 `source.trg_transactions_updated_at` 会在每次更新交易记录前自动刷新 `updated_at`。

## `source.loans`

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `loan_id` | `BIGINT` | 否 | Identity，PK | 贷款合同唯一标识 |
| `customer_id` | `BIGINT` | 否 | FK → `customers.customer_id`，删除受限 | 借款客户 |
| `contract_amount` | `NUMERIC(18,2)` | 否 | `> 0` | 贷款合同金额 |
| `loan_status` | `VARCHAR(20)` | 否 | `PENDING/ACTIVE/PAID_OFF/CANCELLED` | 贷款当前状态 |
| `contract_date` | `DATE` | 否 |  | 合同签订日期 |
| `created_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 记录创建时间 |

索引：`(customer_id)`。

## `source.loan_disbursements`

一笔贷款可以分多次放款，只有状态为 `SUCCESS` 的记录通常计入累计放款金额。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `disbursement_id` | `BIGINT` | 否 | Identity，PK | 放款事件唯一标识 |
| `loan_id` | `BIGINT` | 否 | FK → `loans.loan_id`，删除受限 | 所属贷款 |
| `disbursement_amount` | `NUMERIC(18,2)` | 否 | `> 0` | 放款金额 |
| `disbursement_status` | `VARCHAR(20)` | 否 | `PENDING/SUCCESS/FAILED/CANCELLED` | 放款状态 |
| `disbursement_time` | `TIMESTAMPTZ` | 否 |  | 放款业务时间 |
| `created_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 记录创建时间 |

唯一约束：`(disbursement_id, loan_id)`；索引：`(loan_id, disbursement_time)`。

## `source.loan_repayments`

一笔贷款可以有多次还款，本金和利息分开记录。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `repayment_id` | `BIGINT` | 否 | Identity，PK | 还款事件唯一标识 |
| `loan_id` | `BIGINT` | 否 | FK → `loans.loan_id`，删除受限 | 所属贷款 |
| `principal_amount` | `NUMERIC(18,2)` | 否 | 默认 `0`，`>= 0` | 本次归还本金 |
| `interest_amount` | `NUMERIC(18,2)` | 否 | 默认 `0`，`>= 0` | 本次支付利息 |
| `repayment_status` | `VARCHAR(20)` | 否 | `PENDING/SUCCESS/FAILED/CANCELLED` | 还款状态 |
| `repayment_time` | `TIMESTAMPTZ` | 否 |  | 还款业务时间 |
| `created_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 记录创建时间 |

本息金额必须至少有一项大于零。索引：`(loan_id, repayment_time)`。

## 表关系

```text
source.customers
  ├─< source.accounts
  │     └─< source.transactions
  └─< source.loans
        ├─< source.loan_disbursements
        └─< source.loan_repayments
```

## DDL 执行顺序

```text
sql/source/ddl/000_create_schemas.sql
sql/source/ddl/001_schema.sql
sql/source/alter/004_add_customer_region.sql
sql/source/alter/005_add_transactions_updated.sql
sql/source/trigger/transaction_updated_at.sql
```
