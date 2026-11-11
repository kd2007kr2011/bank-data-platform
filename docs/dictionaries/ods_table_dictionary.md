# ODS 层表结构字典

> 依据：`sql/ods/ddl/*.sql`、`sql/metadata/etl_runs.sql`；更新日期：2026-11-11。
> 本文结构已与实际部署库 `bank_dev`（PostgreSQL 18.6）逐字段核对；"当前行数"取自部署库快照。

## 表清单

| 表名 | 用途 | 数据粒度 | 主键/唯一键 | 当前行数 |
|---|---|---|---|---:|
| `ods.ods_transaction` | 按装载批次保留源交易记录，用于追溯和重跑 | 一个批次中的一笔交易 | PK `ods_id`；UK `(batch_id, transaction_id)` | 30,934 |
| `ods.transaction_current` | 保存每笔交易的最新状态 | 一笔业务交易一行 | PK `transaction_id` | 15,467 |
| `ods.rejected_records` | 保存未通过质量规则的原始记录 | 一条记录违反一条规则 | PK `reject_id`；UK `(source_table, record_hash, rule_code)` | 5 |

`ods.ods_transaction` 的行数约为 `transaction_current` 的两倍，是因为全量装载与增量装载各写入了同一批交易，批次靠 `batch_id` 区分。

## `ods.ods_transaction`

来源：`source.transactions`，另加装载审计字段。ODS 层不额外限制交易类型和状态，以保留源数据原貌。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `ods_id` | `BIGINT` | 否 | Identity，PK | ODS 技术主键 |
| `transaction_id` | `BIGINT` | 否 | UK 组成列 | 源交易唯一标识 |
| `account_id` | `BIGINT` | 否 |  | 交易所属账户标识 |
| `transaction_type` | `VARCHAR(20)` | 否 |  | 源交易类型，原样保留 |
| `amount` | `NUMERIC(18,2)` | 否 |  | 交易金额 |
| `transaction_status` | `VARCHAR(20)` | 否 |  | 源交易状态，原样保留 |
| `transaction_time` | `TIMESTAMPTZ` | 否 |  | 交易业务发生时间 |
| `created_at` | `TIMESTAMPTZ` | 否 |  | Source 记录创建时间 |
| `batch_id` | `VARCHAR(100)` | 否 | UK 组成列 | 装载批次标识 |
| `load_time` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 数据进入 ODS 的时间 |
| `source_system` | `VARCHAR(50)` | 否 | `'bank_core'` | 来源系统标识 |

索引：`(transaction_id, load_time DESC, ods_id DESC)`、`(batch_id)`。

## `ods.transaction_current`

该表是一张当前状态表，不保留同一交易的多个历史版本。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `transaction_id` | `BIGINT` | 否 | PK | 交易唯一标识 |
| `account_id` | `BIGINT` | 否 |  | 交易所属账户标识 |
| `transaction_type` | `VARCHAR(20)` | 否 |  | 交易类型 |
| `amount` | `NUMERIC(18,2)` | 否 |  | 交易金额 |
| `transaction_status` | `VARCHAR(20)` | 否 |  | 当前交易状态 |
| `transaction_time` | `TIMESTAMPTZ` | 否 |  | 交易发生时间 |
| `created_at` | `TIMESTAMPTZ` | 否 |  | 源记录创建时间 |
| `updated_at` | `TIMESTAMPTZ` | 否 |  | 源记录最后更新时间，用于增量判断 |
| `batch_id` | `BIGINT` | 否 |  | 最近一次装载批次标识 |
| `loaded_at` | `TIMESTAMPTZ` | 否 | `CURRENT_TIMESTAMP` | 当前版本写入 ODS 的时间 |

索引：`(updated_at)`。

> 注意：本表的 `batch_id` 是 `BIGINT`，而 `ods.ods_transaction.batch_id` 是 `VARCHAR(100)`。跨表使用批次号时需要显式统一类型。

## `ods.rejected_records`

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `reject_id` | `BIGINT` | 否 | Identity，PK | 拒绝记录技术主键 |
| `source_table` | `VARCHAR(100)` | 否 | UK 组成列 | 发生质量问题的来源表 |
| `batch_id` | `VARCHAR(100)` | 否 |  | 装载批次标识 |
| `source_record_key` | `VARCHAR(200)` | 是 |  | 来源记录业务键；无法确定时可空 |
| `raw_data` | `JSONB` | 否 |  | 被拒绝记录的原始内容 |
| `rule_code` | `VARCHAR(100)` | 否 | UK 组成列 | 数据质量规则编码 |
| `reject_reason` | `TEXT` | 否 |  | 拒绝原因说明 |
| `record_hash` | `VARCHAR(64)` | 否 | UK 组成列 | 原始记录摘要，用于幂等去重 |
| `rejected_at` | `TIMESTAMPTZ` | 否 | `NOW()` | 记录被拒绝的时间 |

## 附：ETL 元数据表（`metadata` schema）

### `metadata.etl_runs`

由 `sql/metadata/etl_runs.sql` 建表，记录每次增量任务的执行情况与水位线，是增量调度判断"从哪儿继续"的依据。

| 字段 | 类型 | 可空 | 约束/默认值 | 含义 |
|---|---|---:|---|---|
| `run_id` | `BIGINT` | 否 | Identity，PK | 运行序号 |
| `job_name` | `VARCHAR(100)` | 否 |  | 任务名，如 `transactions_incremental` |
| `status` | `VARCHAR(20)` | 否 | `RUNNING/SUCCESS/FAILED` | 运行状态 |
| `watermark_start` | `TIMESTAMPTZ` | 是 |  | 本次增量起点 |
| `watermark_end` | `TIMESTAMPTZ` | 是 |  | 本次增量终点，即新的水位线 |
| `started_at` | `TIMESTAMP` | 否 | `CURRENT_TIMESTAMP` | 开始时间 |
| `finished_at` | `TIMESTAMP` | 是 |  | 结束时间 |
| `rows_extracted` | `BIGINT` | 是 | 默认 `0` | 抽取行数 |
| `rows_loaded` | `BIGINT` | 是 | 默认 `0` | 装载行数 |
| `error_message` | `TEXT` | 是 |  | 失败时的错误信息 |

当前行数：5。

## 主要血缘

```text
source.transactions
  ├─> ods.ods_transaction       （批次历史）
  └─> ods.transaction_current   （最新状态）

装载质量检查失败
  └─> ods.rejected_records

增量任务执行
  └─> metadata.etl_runs         （运行状态与水位线）
```
