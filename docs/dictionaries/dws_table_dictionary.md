# DWS 层表结构字典

> 依据：`sql/dws/**/*.sql`；更新日期：2026-11-11。
> 本文结构已与实际部署库 `bank_dev`（PostgreSQL 18.6）逐字段核对，字段类型、约束、当前行数均取自数据库。

DWS（Data Warehouse Service）层承接 DWD 明细，按"主题 + 统计日期"做轻度汇总，为上层报表和指标分析提供可直接查询的结果集。

## 表清单

| 表名 | 主题 | 数据粒度 | 主要用途 | 当前行数 |
|---|---|---|---|---:|
| `dws.dws_customer_transaction_daily` | 客户交易 | 一个客户 × 一个业务日期 | 客户日交易笔数与成功金额 | 14,477 |
| `dws.dws_region_transaction_daily` | 地区交易 | 一个地区 × 一个业务日期 | 地区日交易笔数与成功金额 | 4,862 |
| `dws.dws_customer_loan_risk_daily` | 客户贷款风险 | 一个客户 × 一个统计日期 | 客户贷款余额与逾期指标 | 286 |
| `dws.dws_region_loan_risk_daily` | 地区贷款风险 | 一个地区 × 一个统计日期 | 地区贷款余额与逾期指标 | 8 |

当前数据范围：交易类汇总覆盖 `2022-04-14 ~ 2026-10-22`；贷款风险类汇总当前只有 `2026-10-31` 一个统计日（贷款快照目前只生成这一天）。

## `dws.dws_customer_transaction_daily`

装载脚本：`sql/dws/load/customer_transaction_daily.sql`（D17）。
数据来源：`dwd.fact_transaction` + `dwd.dim_date`。
执行方式：`TRUNCATE` 后全量重建，天然幂等。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `business_date` | `DATE` | 否 | PK 组成列 | 交易业务日期（取自 `dim_date.full_date`） |
| `customer_key` | `BIGINT` | 否 | PK 组成列 | 客户代理键，对应 `dwd.dim_customer.customer_key` |
| `total_transaction_count` | `BIGINT` | 否 | 默认 `0` | 当日该客户全部状态的交易笔数 |
| `success_count` | `BIGINT` | 否 | 默认 `0` | 当日状态为 `SUCCESS` 的交易笔数 |
| `success_amount` | `NUMERIC(20,2)` | 否 | 默认 `0` | 当日成功交易金额合计 |
| `dw_load_time` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 汇总写入时间 |

统计口径：笔数统计包含所有交易状态；金额只累计 `SUCCESS`；无成功交易的客户日不落库（因此没有零值行）。

## `dws.dws_region_transaction_daily`

装载脚本：`sql/dws/load/region_transaction_daily.sql`（D17）。
数据来源：`dwd.fact_transaction` + `dwd.dim_date`。
执行方式：`TRUNCATE` 后全量重建。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `business_date` | `DATE` | 否 | UK 组成列 | 交易业务日期 |
| `region_key` | `BIGINT` | 是 | FK → `dwd.dim_region.region_key` | 地区代理键；`NULL` 表示未知地区 |
| `total_transaction_count` | `BIGINT` | 否 | 默认 `0` | 当日该地区全部状态的交易笔数 |
| `success_count` | `BIGINT` | 否 | 默认 `0` | 当日状态为 `SUCCESS` 的交易笔数 |
| `success_amount` | `NUMERIC(20,2)` | 否 | 默认 `0` | 当日成功交易金额合计 |
| `dw_load_time` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 汇总写入时间 |

约束：

- `uq_dws_region_transaction_daily`：`UNIQUE NULLS NOT DISTINCT (business_date, region_key)`，保证 `region_key` 为 `NULL` 时同一天也只保留一行。
- `fk_dws_region_transaction_daily_region`：外键指向 `dwd.dim_region(region_key)`。

> 该表是 DWS 中唯一带外键约束的表；另外三张汇总表只靠主键和上游装载保证一致性。

## `dws.dws_customer_loan_risk_daily`

装载脚本：`sql/dws/load/customer_loan_risk_daily.sql`（D18）。
数据来源：`dwd.fact_loan_daily` + `dwd.dim_date`。
执行方式：按 `(business_date, customer_key)` 幂等 `ON CONFLICT DO UPDATE`，可重复执行。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `business_date` | `DATE` | 否 | PK 组成列 | 统计日期（取自 `dim_date.full_date`） |
| `customer_key` | `BIGINT` | 否 | PK 组成列 | 客户代理键 |
| `loan_count` | `INTEGER` | 否 | 默认 `0` | 当日有余额的贷款笔数 |
| `loan_balance` | `NUMERIC(18,2)` | 否 | 默认 `0` | 当日贷款未偿本金合计 |
| `overdue_loan_count` | `INTEGER` | 否 | 默认 `0` | 其中 `overdue_days > 0` 的贷款笔数 |
| `overdue_balance` | `NUMERIC(18,2)` | 否 | 默认 `0` | 逾期贷款的未偿本金合计 |
| `overdue_rate` | `NUMERIC(10,6)` | 否 | 默认 `0` | 逾期率 = 逾期余额 / 贷款总余额 |
| `created_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 记录首次写入时间 |
| `updated_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 重跑更新时间 |

统计口径：

1. 逾期判定：`fact_loan_daily.overdue_days > 0`。
2. 逾期余额取逾期贷款的**全部**未偿本金，不按逾期天数分摊。
3. 逾期率分母为 0 时用 `NULLIF` 兜底并 `COALESCE` 为 0。
4. 当前 `dwd.dwd_loan_snapshot.overdue_days` 由 ETL 恒写入 `NULL`，`fact_loan_daily` 落库时 `COALESCE` 为 0，因此现阶段 `overdue_loan_count` 与 `overdue_balance` 恒为 0；等逾期规则补齐后该表会自动反映真实逾期。

## `dws.dws_region_loan_risk_daily`

装载脚本：`sql/dws/load/region_loan_risk_daily.sql`（D18）。
数据来源：`dwd.fact_loan_daily` + `dwd.dim_date`。
执行方式：按 `(business_date, region_key)` 幂等 `ON CONFLICT DO UPDATE`。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `business_date` | `DATE` | 否 | PK 组成列 | 统计日期 |
| `region_key` | `BIGINT` | 否 | PK 组成列 | 地区代理键，不允许为空 |
| `loan_count` | `INTEGER` | 否 | 默认 `0` | 当日该地区有余额的贷款笔数 |
| `loan_balance` | `NUMERIC(18,2)` | 否 | 默认 `0` | 当日该地区贷款未偿本金合计 |
| `overdue_loan_count` | `INTEGER` | 否 | 默认 `0` | 其中 `overdue_days > 0` 的贷款笔数 |
| `overdue_balance` | `NUMERIC(18,2)` | 否 | 默认 `0` | 逾期贷款未偿本金合计 |
| `overdue_rate` | `NUMERIC(10,6)` | 否 | 默认 `0` | 逾期率 = 逾期余额 / 贷款总余额 |
| `created_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 记录首次写入时间 |
| `updated_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 重跑更新时间 |

> 口径与客户版完全一致，仅聚合维度由客户换成地区。
> 该表的 `region_key` 来自 `dwd.fact_loan_daily.region_key` 且不允许为 `NULL`：若上游出现地区未知的贷款，本表会因 `NOT NULL` 约束报错。当前 `dim_customer.region_key` 与两张事实表的 `region_key` 均无空值，可以正常装载。

## 主要血缘

```text
dwd.fact_transaction + dwd.dim_date
  ├─> dws.dws_customer_transaction_daily
  └─> dws.dws_region_transaction_daily

dwd.fact_loan_daily + dwd.dim_date
  ├─> dws.dws_customer_loan_risk_daily
  └─> dws.dws_region_loan_risk_daily
```

上下游对照：

| DWS 表 | 上游事实表 | 代理键来源 |
|---|---|---|
| `dws_customer_transaction_daily` | `dwd.fact_transaction` | `fact_transaction.customer_key` |
| `dws_region_transaction_daily` | `dwd.fact_transaction` | `fact_transaction.region_key` |
| `dws_customer_loan_risk_daily` | `dwd.fact_loan_daily` | `fact_loan_daily.customer_key` |
| `dws_region_loan_risk_daily` | `dwd.fact_loan_daily` | `fact_loan_daily.region_key` |

## 使用注意

1. 四张表都没有指向 `dwd.dim_customer` / `dwd.dim_region` 的外键（除 `dws_region_transaction_daily.region_key`），维度缺失不会在入库时被发现，查询时建议先做一次关联完整性核对。
2. 交易类汇总用 `TRUNCATE` + `INSERT` 全量重建，贷款风险类用 `ON CONFLICT` 增量更新，两种方式的执行语义不同，不要混用脚本。
3. `business_date` 存的是真实日期，不是 `date_key` 形式的 `YYYYMMDD` 整数，跨层聚合时注意类型差异。
