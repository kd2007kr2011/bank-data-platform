# DWD 层表结构字典

> 依据：`sql/dwd/ddl/*.sql`、`sql/dwd/dimensions.sql`；更新日期：2026-11-10。`sql/dwd/demo/` 下的演示表不属于正式 DWD 表清单。

## 表清单

| 分类 | 表名 | 数据粒度 | 主要用途 |
|---|---|---|---|
| 标准明细 | `dwd.dwd_transaction_detail` | 一笔交易一行 | 去重后的当前交易明细 |
| 标准明细 | `dwd.dwd_loan` | 一笔贷款合同一行 | 贷款合同标准明细 |
| 标准事件 | `dwd.dwd_repayment_event` | 一笔还款事件一行 | 贷款还款事件明细 |
| 日快照 | `dwd.dwd_loan_snapshot` | 一笔贷款、一个快照日一行 | 贷款本金累计及余额 |
| 维度 | `dwd.dim_region` | 一个地区一行 | 地区维度 |
| 维度 | `dwd.dim_customer` | 一个客户一行 | 客户维度（SCD Type 1） |
| 维度 | `dwd.dim_date` | 一个自然日一行 | 日期维度 |
| 事实 | `dwd.fact_transaction` | 一笔交易一行 | 星型模型交易事实 |
| 事实 | `dwd.fact_loan_daily` | 一笔贷款、一个日期一行 | 星型模型贷款日事实 |

## `dwd.dwd_transaction_detail`

执行 `ddl.sql` 后还应执行 `alter_transaction.sql`；下表展示变更后的最终结构。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `transaction_id` | `BIGINT` | 否 | PK | 交易唯一标识 |
| `account_id` | `BIGINT` | 否 |  | 账户标识 |
| `transaction_type` | `VARCHAR(20)` | 否 | `DEPOSIT/WITHDRAWAL/TRANSFER` | 标准交易类型 |
| `amount` | `NUMERIC(18,2)` | 否 | `> 0` | 交易金额 |
| `transaction_status` | `VARCHAR(20)` | 否 | `PENDING/SUCCESS/FAILED/CANCELLED/REVERSED` | 标准交易状态 |
| `transaction_time` | `TIMESTAMP` | 否 |  | 交易发生时间 |
| `transaction_date` | `DATE` | 否 | 按 `Asia/Shanghai` 从交易时间派生 | 交易业务日期 |
| `source_created_at` | `TIMESTAMP` | 否 |  | 源记录创建时间 |
| `source_batch_id` | `VARCHAR(100)` | 否 |  | 来源 ODS 批次标识 |
| `ods_load_time` | `TIMESTAMPTZ` | 否 |  | 来源记录进入 ODS 的时间 |
| `dw_load_time` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | DWD 写入/更新时间 |
| `source_updated_at` | `TIMESTAMPTZ` | 是 | 由 D12 变更脚本添加 | 源记录最后更新时间 |

`ods_id` 在初始 DDL 中创建，但会被 D12 变更脚本删除。索引：`(transaction_date, transaction_status)`、`(account_id, transaction_time)`。

## `dwd.dwd_loan`

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `loan_id` | `BIGINT` | 否 | PK | 贷款唯一标识 |
| `customer_id` | `BIGINT` | 否 |  | 借款客户标识 |
| `contract_amount` | `NUMERIC(18,2)` | 否 | `> 0` | 合同金额 |
| `loan_status` | `VARCHAR(20)` | 否 | `PENDING/ACTIVE/PAID_OFF/CANCELLED` | 贷款当前状态 |
| `contract_date` | `DATE` | 否 |  | 合同日期 |
| `source_created_at` | `TIMESTAMPTZ` | 是 |  | 源记录创建时间 |
| `etl_updated_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | ETL 最近更新时间 |

## `dwd.dwd_repayment_event`

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `repayment_id` | `BIGINT` | 否 | PK | 还款事件唯一标识 |
| `loan_id` | `BIGINT` | 否 | FK → `dwd_loan.loan_id` | 所属贷款标识 |
| `principal_amount` | `NUMERIC(18,2)` | 否 | `>= 0` | 归还本金 |
| `interest_amount` | `NUMERIC(18,2)` | 否 | `>= 0` | 支付利息；本息合计须大于 0 |
| `repayment_status` | `VARCHAR(20)` | 否 | `PENDING/SUCCESS/FAILED/CANCELLED` | 还款状态 |
| `repayment_time` | `TIMESTAMPTZ` | 否 |  | 还款业务时间 |
| `source_created_at` | `TIMESTAMPTZ` | 是 |  | 源记录创建时间 |
| `etl_updated_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | ETL 最近更新时间 |

## `dwd.dwd_loan_snapshot`

仓库存在两份同名表定义。建议以 `sql/dwd/ddl/ddl.sql` 的 D08 版本为主，因为对应 ETL `build_loan_snapshot.py` 使用了其中的客户、合同及装载字段。

### 主版本（`ddl.sql`）

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `loan_id` | `BIGINT` | 否 | 联合 PK | 贷款标识 |
| `snapshot_date` | `DATE` | 否 | 联合 PK；不早于合同日 | 快照业务日期 |
| `customer_id` | `BIGINT` | 否 |  | 客户标识 |
| `contract_date` | `DATE` | 否 |  | 合同日期 |
| `contract_amount` | `NUMERIC(18,2)` | 否 | `> 0` | 合同金额 |
| `total_disbursed` | `NUMERIC(18,2)` | 否 | 默认 `0`，`>= 0` | 截至快照日累计成功放款 |
| `total_principal_repaid` | `NUMERIC(18,2)` | 否 | 默认 `0`，`>= 0` | 截至快照日累计成功归还本金 |
| `outstanding_principal` | `NUMERIC(18,2)` | 否 | 生成列 | `total_disbursed - total_principal_repaid` |
| `dw_load_time` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 快照写入/重算时间 |

### 另一版本（`loan.sql`）的差异

该版本保留 `loan_id`、`snapshot_date`、`total_disbursed`、`total_principal_repaid`、`outstanding_principal`，但增加 `total_interest_paid`、`overdue_days`、`etl_updated_at`，删除 `customer_id`、`contract_date`、`contract_amount`、`dw_load_time`，并增加到 `dwd_loan` 的外键。由于使用 `CREATE TABLE IF NOT EXISTS`，先执行哪份脚本将决定实际结构，后执行的脚本不会自动补齐字段。

## 维度表

### `dwd.dim_region`

| 字段 | 类型 | 约束 | 含义 |
|---|---|---|---|
| `region_key` | `BIGINT` Identity | PK | 地区代理键 |
| `region_name` | `VARCHAR(100)` | UK，非空字符串 | 地区名称 |
| `created_at` | `TIMESTAMPTZ` | 默认当前时间 | 创建时间 |
| `updated_at` | `TIMESTAMPTZ` | 默认当前时间 | 更新时间 |

### `dwd.dim_customer`

| 字段 | 类型 | 约束 | 含义 |
|---|---|---|---|
| `customer_key` | `BIGINT` Identity | PK | 客户代理键 |
| `customer_id` | `VARCHAR(64)` | UK | 源客户业务键 |
| `region_key` | `BIGINT` | 可空，FK → `dim_region` | 所属地区代理键 |
| `created_at` | `TIMESTAMPTZ` | 默认当前时间 | 创建时间 |
| `updated_at` | `TIMESTAMPTZ` | 默认当前时间 | 更新时间 |

### `dwd.dim_date`

| 字段 | 类型 | 约束 | 含义 |
|---|---|---|---|
| `date_key` | `INTEGER` | PK，格式 `YYYYMMDD` | 日期代理键 |
| `full_date` | `DATE` | UK | 完整日期 |
| `year_num` | `INTEGER` | 非空 | 年 |
| `quarter_num` | `INTEGER` | 1–4 | 季度 |
| `month_num` | `INTEGER` | 1–12 | 月 |
| `day_num` | `INTEGER` | 非空 | 日 |
| `week_num` | `INTEGER` | 非空 | ISO 周序号 |
| `day_of_week` | `INTEGER` | 1–7 | ISO 星期序号 |
| `is_weekend` | `BOOLEAN` | 非空 | 是否周末 |

## 事实表

### `dwd.fact_transaction`

| 字段 | 类型 | 约束/含义 |
|---|---|---|
| `transaction_key` | `BIGINT` Identity | PK，交易事实代理键 |
| `transaction_id` | `VARCHAR(64)` | UK，源交易业务键 |
| `customer_key` | `BIGINT` | FK → `dim_customer` |
| `region_key` | `BIGINT` | 可空，FK → `dim_region` |
| `date_key` | `INTEGER` | FK → `dim_date` |
| `account_id` | `VARCHAR(64)` | 可空，账户业务键 |
| `transaction_time` | `TIMESTAMPTZ` | 交易时间 |
| `transaction_type` | `VARCHAR(32)` | `DEPOSIT/WITHDRAWAL/TRANSFER` |
| `transaction_status` | `VARCHAR(32)` | `PENDING/SUCCESS/FAILED/CANCELLED/REVERSED` |
| `amount` | `NUMERIC(18,2)` | `> 0` |
| `created_at` | `TIMESTAMPTZ` | 默认当前时间 |
| `updated_at` | `TIMESTAMPTZ` | 默认当前时间 |

事实表与 `dwd_transaction_detail` 使用相同的五种交易状态，保留完整交易生命周期。

### `dwd.fact_loan_daily`

| 字段 | 类型 | 约束/含义 |
|---|---|---|
| `loan_daily_key` | `BIGINT` Identity | PK，贷款日事实代理键 |
| `loan_id` | `VARCHAR(64)` | 与 `date_key` 组成 UK |
| `customer_key` | `BIGINT` | FK → `dim_customer` |
| `region_key` | `BIGINT` | 可空，FK → `dim_region` |
| `date_key` | `INTEGER` | FK → `dim_date` |
| `total_disbursed` | `NUMERIC(18,2)` | 默认 `0`，`>= 0` |
| `total_repaid_principal` | `NUMERIC(18,2)` | 默认 `0`，`>= 0` |
| `outstanding_principal` | `NUMERIC(18,2)` | 默认 `0`，`>= 0` |
| `overdue_days` | `INTEGER` | 默认 `0`，`>= 0` |
| `created_at` | `TIMESTAMPTZ` | 默认当前时间 |
| `updated_at` | `TIMESTAMPTZ` | 默认当前时间 |

## 主要血缘

```text
ods.ods_transaction / ods.transaction_current
  └─> dwd.dwd_transaction_detail
        └─> dwd.fact_transaction

source.loans
  └─> dwd.dwd_loan

source.loan_repayments
  └─> dwd.dwd_repayment_event

source.loans + source.loan_disbursements + source.loan_repayments
  └─> dwd.dwd_loan_snapshot
        └─> dwd.fact_loan_daily
```
