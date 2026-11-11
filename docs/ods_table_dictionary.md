# ODS 层表结构字典

> 依据：`sql/ods/ddl/*.sql`；更新日期：2026-11-10。本文描述仓库代码中的结构，不代表某个已部署数据库的实时状态。

## 表清单

| 表名 | 用途 | 数据粒度 | 主键/唯一键 |
|---|---|---|---|
| `ods.ods_transaction` | 按装载批次保留源交易记录，用于追溯和重跑 | 一个批次中的一笔交易 | PK `ods_id`；UK `(batch_id, transaction_id)` |
| `ods.transaction_current` | 保存每笔交易的最新状态 | 一笔业务交易一行 | PK `transaction_id` |
| `ods.rejected_records` | 保存未通过质量规则的原始记录 | 一条记录违反一条规则 | PK `reject_id`；UK `(source_table, record_hash, rule_code)` |

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

## 主要血缘

```text
source.transactions
  ├─> ods.ods_transaction       （批次历史）
  └─> ods.transaction_current   （最新状态）

装载质量检查失败
  └─> ods.rejected_records
```
