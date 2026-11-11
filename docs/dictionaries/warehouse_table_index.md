# 数仓表文档索引

本项目的表结构文档按数据层拆分：

| 数据层 | 文档 | 内容 |
|---|---|---|
| Source | [source_table_dictionary.md](source_table_dictionary.md) | Source 表清单、最终字段、约束、索引和表关系 |
| ODS | [ods_table_dictionary.md](ods_table_dictionary.md) | ODS 表清单、字段、约束、血缘，以及 `metadata.etl_runs` |
| DWD | [dwd_table_dictionary.md](dwd_table_dictionary.md) | DWD 明细、快照、维度、事实表字段字典及重跑审计表 |
| DWS | [dws_table_dictionary.md](dws_table_dictionary.md) | DWS 客户/地区交易汇总与贷款风险汇总字段字典 |

已有的 [data_dictionary.md](data_dictionary.md) 保留为更详细的 Source 业务规则说明；`source_table_dictionary.md` 用于和 ODS、DWD、DWS 文档保持统一结构。

## 分层与主题速查

| Schema | 表 | 粒度 | 主题 |
|---|---|---|---|
| `source` | `customers` / `accounts` / `transactions` / `loans` / `loan_disbursements` / `loan_repayments` | 一行一业务实体 | 源业务数据 |
| `ods` | `ods_transaction` / `transaction_current` / `rejected_records` | 一行一批次交易 / 一行一交易 / 一行一规则命中 | 贴源与坏数据隔离 |
| `dwd` | `dwd_transaction_detail` / `dwd_loan` / `dwd_repayment_event` / `dwd_loan_snapshot` | 明细与快照 | 清洗后的标准明细 |
| `dwd` | `dim_region` / `dim_customer` / `dim_date` | 一行一维度成员 | 星型模型维度 |
| `dwd` | `fact_transaction` / `fact_loan_daily` | 一笔交易 / 一笔贷款一个日期 | 星型模型事实 |
| `dws` | `dws_customer_transaction_daily` / `dws_region_transaction_daily` | 一主体一业务日期 | 客户与地区交易汇总 |
| `dws` | `dws_customer_loan_risk_daily` / `dws_region_loan_risk_daily` | 一主体一统计日期 | 客户与地区贷款风险汇总 |
| `metadata` | `etl_runs` | 一次任务运行 | 增量水位线与运行状态 |

## 维护规则

1. 新增或修改 DDL 时，同步修改对应层的表结构字典。
2. 字段类型、可空性、默认值和状态集合以 SQL DDL 为准，并以实际部署库 `bank_dev` 复核。
3. 同名表存在多份 DDL 时，应在文档中写明执行顺序和最终结构。
4. 演示表、临时表与正式表分开记录，不混入正式表清单。
5. 各字典中的"当前行数"是核对时的部署库快照，会随 ETL 运行变化，只作规模参考。
