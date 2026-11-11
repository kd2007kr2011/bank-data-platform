# DWD 层表结构字典

> 依据：`sql/dwd/ddl/*.sql`、`sql/dwd/demo/loan_snapshot_demo.sql`；更新日期：2026-11-11。
> 本文结构已与实际部署库 `bank_dev`（PostgreSQL 18.6）逐字段核对；"当前行数"取自部署库快照。
> `sql/dwd/demo/` 下的 `dwd.loan_snapshot_d14_demo`、临时表 `dwd.tmp_chk` 不属于正式 DWD 表清单。

## 表清单

| 分类 | 表名 | 数据粒度 | 主要用途 | 当前行数 |
|---|---|---|---|---:|
| 标准明细 | `dwd.dwd_transaction_detail` | 一笔交易一行 | 去重后的当前交易明细 | 15,467 |
| 标准明细 | `dwd.dwd_loan` | 一笔贷款合同一行 | 贷款合同标准明细 | 286 |
| 标准事件 | `dwd.dwd_repayment_event` | 一笔还款事件一行 | 贷款还款事件明细 | 286 |
| 日快照 | `dwd.dwd_loan_snapshot` | 一笔贷款、一个快照日一行 | 贷款本金累计及余额 | 286 |
| 维度 | `dwd.dim_region` | 一个地区一行 | 地区维度 | 8 |
| 维度 | `dwd.dim_customer` | 一个客户一行 | 客户维度（SCD Type 1） | 1,000 |
| 维度 | `dwd.dim_date` | 一个自然日一行 | 日期维度 | 5,844 |
| 事实 | `dwd.fact_transaction` | 一笔交易一行 | 星型模型交易事实 | 15,467 |
| 事实 | `dwd.fact_loan_daily` | 一笔贷款、一个日期一行 | 星型模型贷款日事实 | 286 |
| 审计 | `dwd.etl_replay_log` | 一次重跑一行 | 贷款快照重跑前后的行数与金额对比 | 10 |

`dwd.dim_date` 由 `sql/dwd/ddl/dimensions.sql` 初始化，覆盖 `2020-01-01 ~ 2035-12-31`（每日一行）。

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

仓库存在两份同名表定义（`sql/dwd/ddl/ddl.sql` 与 `sql/dwd/ddl/loan.sql`），两者都用 `CREATE TABLE IF NOT EXISTS`，先执行的脚本决定实际结构。**部署库当前生效的是 `loan.sql` 版本**（字段与实际库一致），下表即按该版本列出。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `snapshot_date` | `DATE` | 否 | 联合 PK | 快照业务日期 |
| `loan_id` | `BIGINT` | 否 | 联合 PK；FK → `dwd.dwd_loan.loan_id` | 贷款标识 |
| `total_disbursed` | `NUMERIC(18,2)` | 否 |  | 截至快照日累计成功放款 |
| `total_principal_repaid` | `NUMERIC(18,2)` | 否 |  | 截至快照日累计成功归还本金 |
| `total_interest_paid` | `NUMERIC(18,2)` | 否 |  | 截至快照日累计已付利息 |
| `outstanding_principal` | `NUMERIC(18,2)` | 否 | `>= 0` | 未偿本金 |
| `overdue_days` | `INTEGER` | 是 | `>= 0` 或 `NULL` | 逾期天数；当前装载恒为 `NULL` |
| `etl_updated_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | ETL 最近更新时间 |

该表**不保存 `customer_id`**：需要客户信息时通过 `loan_id` 关联 `dwd.dwd_loan` 取 `customer_id`。`sql/dwd/load/load_fact_loan_daily.sql` 就是按这条链路取客户代理键的。

### 另一版本（`ddl.sql`）的差异

`ddl.sql` 的 D08 版本保留 `loan_id`、`snapshot_date`、`customer_id`、`contract_date`、`contract_amount`、`total_disbursed`、`total_principal_repaid`、`outstanding_principal`（生成列）、`dw_load_time`，但没有 `total_interest_paid`、`overdue_days`、`etl_updated_at`，也没有到 `dwd_loan` 的外键。两版字段不兼容，后执行的脚本不会自动补齐字段，切换版本前需先删表重建。

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

## 审计表

### `dwd.etl_replay_log`

由 `sql/dwd/demo/loan_snapshot_demo.sql` 建表，由 `etl/dwd/build_loan_snapshot.py` 在重跑贷款快照时写入：每次重跑记录该快照日重算前后的行数与金额合计，用于对比重跑结果是否一致。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `run_id` | `BIGINT` | 否 | PK，`BIGSERIAL` | 重跑序号 |
| `snapshot_date` | `DATE` | 否 |  | 重跑对应的快照日 |
| `run_reason` | `TEXT` | 否 |  | 重跑原因说明 |
| `old_count` | `INTEGER` | 否 |  | 重跑前行数 |
| `new_count` | `INTEGER` | 否 |  | 重跑后行数 |
| `old_total` | `NUMERIC(20,2)` | 否 |  | 重跑前未偿本金合计 |
| `new_total` | `NUMERIC(20,2)` | 否 |  | 重跑后未偿本金合计 |
| `executed_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 重跑执行时间 |

## 主要血缘

```text
source.customers
  └─> dwd.dim_region
        └─> dwd.dim_customer

ods.ods_transaction / ods.transaction_current
  └─> dwd.dwd_transaction_detail
        └─> dwd.fact_transaction
              └─> dws.dws_customer_transaction_daily
              └─> dws.dws_region_transaction_daily

source.loans
  └─> dwd.dwd_loan

source.loan_repayments
  └─> dwd.dwd_repayment_event

source.loans + source.loan_disbursements + source.loan_repayments
  └─> dwd.dwd_loan_snapshot
        └─> dwd.fact_loan_daily
              └─> dws.dws_customer_loan_risk_daily
              └─> dws.dws_region_loan_risk_daily
```

装载脚本对照：

| 表 | 装载脚本 |
|---|---|
| `dwd.dwd_transaction_detail` | `etl/dwd/build_dwd_transactions.py`、`sql/dwd/transform/transaction.sql` |
| `dwd.dwd_loan` | `etl/dwd/build_dwd_loans.py` |
| `dwd.dwd_loan_snapshot` | `etl/dwd/build_loan_snapshot.py`、`sql/dwd/transform/loan_snapshot.sql` |
| `dwd.dim_region` / `dwd.dim_customer` | `etl/dwd/build_dimensions.py` |
| `dwd.dim_date` | `sql/dwd/ddl/dimensions.sql`（初始化脚本） |
| `dwd.fact_transaction` | `sql/dwd/load/load_fact_transaction.sql` |
| `dwd.fact_loan_daily` | `sql/dwd/load/load_fact_loan_daily.sql` |

> `dwd.fact_loan_daily.region_key` 取自 `dwd.dim_customer.region_key`（客户当前地区，SCD Type 1），不是贷款自身的地区；`customer_key` 需经 `dwd.dwd_loan.customer_id` 中转，快照表本身不存客户字段。
