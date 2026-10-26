# D08 学习记录：数据仓库分层设计与粒度定义

**学习日期：** 2026-10-26  
**项目：** 零售银行数据平台（bank-data-platform）  
**主题：** Source、ODS、DWD 分层设计，表粒度、主键及时间字段

## 1. 今日学习目标

- 理解为什么要建设分层数据仓库，以及 Source、ODS、DWD、DWS、ADS 的职责。
- 掌握“粒度”的概念，区分业务主键、技术主键和导入批次。
- 基于现有 Source 六张业务表，设计 `ods.ods_transaction`、`dwd.dwd_transaction_detail`、`dwd.dwd_loan_snapshot`。
- 梳理字段映射、业务时间、入仓时间和后续的增量策略。

## 2. 对数据仓库分层的理解

### 2.1 为什么要分层

Source 用于保存业务系统产生的数据，例如客户开户、账户交易、贷款合同、放款和还款。如果分析任务长期直接查询 Source，不仅可能反复执行相同的清洗、关联和汇总逻辑，还会增加业务数据库的查询负担。因此，将数据按不同职责组织成独立层次，便于复用、追溯和维护。

```text
Source（源业务数据）
  ↓ 按规则抽取 / 同步
ODS（保留接入数据和批次信息）
  ↓ 清洗、去重、标准化
DWD（统一口径的明细事实）
  ↓ 按业务主题汇总
DWS（可复用的公共指标和汇总结果）
  ↓ 按报表、应用需求组织
ADS（面向具体应用的数据服务）
  ↓ 查询 / 刷新
报表、看板等业务应用
```

### 2.2 各层职责

| 层级 | 主要职责 | 银行项目示例 |
|---|---|---|
| Source | 记录真实业务活动和当前业务数据 | `source.transactions`、`source.loans` |
| ODS | 接入源数据，保留尽可能原始的字段以及来源、批次、载入时间 | `ods.ods_transaction` |
| DWD | 清洗、统一状态和字段口径，形成粒度明确的明细记录 | `dwd.dwd_transaction_detail`、`dwd.dwd_loan_snapshot` |
| DWS | 按通用分析主题进行汇总，减少重复计算 | 月交易金额、月活跃客户数 |
| ADS | 为特定报表、业务应用提供适合直接读取的结果 | 经营报表、风险监控看板 |

**认识：** 数据仓库分层不是简单将同一份数据复制多遍，而是将数据接入、加工、汇总和应用服务的职责分开。

## 3. ODS 的批次与可追溯性

交易数据会持续产生，ODS 可以按日或按其他调度周期同步；每次导入使用一个 `batch_id`，并记录 `load_time`。例如，同一笔交易可能在第一次导入时是 `PENDING`，在后续批次中成为 `SUCCESS`。

| ods_id | transaction_id | transaction_status | batch_id |
|---:|---:|---|---|
| 1 | 10001 | PENDING | batch_001 |
| 2 | 10001 | SUCCESS | batch_002 |

本项目的 ODS 表中：

- `transaction_id`：源业务交易编号；不同批次可以重复。
- `batch_id`：标识一次数据导入任务，不等于单行主键。
- `ods_id`：ODS 记录的独立技术主键。
- `UNIQUE (batch_id, transaction_id)`：约束同一批次的同一笔交易不重复存储（这是本项目选择的批次粒度）。
- `load_time`：数据进入 ODS 的时间，与交易实际发生时间不同。

**边界：** ODS 不一定只能增量导入，也可以做全量快照。批次能够追溯“同步时看到的记录”，但如果源表在两个同步批次之间发生多次变化而没有变更日志，仅靠批次无法还原每一次中间状态。延迟到达数据需要结合业务时间和入仓时间处理。

## 4. DWD 的粒度与两类表

**粒度：一行记录代表的业务对象或业务事实。粒度决定主键及能否正确汇总、关联。**

### 4.1 交易明细表

`dwd.dwd_transaction_detail`：**一笔交易一行**，使用 `transaction_id` 作为业务主键。与 ODS 不同，同一交易的多个同步版本不直接成为多笔 DWD 交易；需要按确定的规则选择或更新标准版本。

映射：

```text
source.transactions
      ↓ 接入并记录 batch_id、load_time
ods.ods_transaction
      ↓ 去重、校验、状态标准化、派生交易日期
dwd.dwd_transaction_detail
```

当前 Source 交易字段为：`transaction_id`、`account_id`、`transaction_type`、`amount`、`transaction_status`、`transaction_time`、`created_at`。

Source 合法交易类型：`DEPOSIT`、`WITHDRAWAL`、`TRANSFER`；状态：`PENDING`、`SUCCESS`、`FAILED`、`CANCELLED`、`REVERSED`。不能漏掉 `REVERSED`。

### 4.2 贷款日快照表

`dwd.dwd_loan_snapshot`：**一笔贷款在一个业务日期一行**，联合主键为 `(loan_id, snapshot_date)`。

其目的是保存不同日期的未偿本金状态，便于查询历史任意一天的贷款余额。每日生成新的快照后，行数会随着日期增长；后续可考虑按日期分区、增量计算和历史归档。

本项目的未偿本金口径：

```text
截至快照日累计成功放款本金
- 截至快照日累计成功归还本金
= 截至快照日未偿还本金
```

- 合同金额 `contract_amount` 不等于实际放款金额。
- 还款表的 `principal_amount` 才参与未偿本金计算，`interest_amount` 不应从本金中扣减。
- 只统计状态为 `SUCCESS` 的放款和还款。
- `source.loans` 提供贷款合同及客户信息，`source.loan_disbursements` 和 `source.loan_repayments` 分别提供事件数据。
- 不能直接拿当前 `source.loans.loan_status` 代表过去每一天的历史状态；历史状态需要有可靠的事件或状态变更依据。
- 当前简化计算不覆盖冲正、核销、减免等更复杂的真实银行场景。

例如，某贷款截至前一日未偿本金为 9000 元，当天没有新增放款、成功归还本金 1000 元，则当天余额为 8000 元。可以每天从历史重新汇总，也可以在可靠对账规则下根据前日余额增量计算。

## 5. 建表时需要重点关注的内容

| 设计内容 | 今日结论 |
|---|---|
| Source 字段对应 | 新表必须与既有字段字典核对，不能凭空使用源表没有的字段 |
| 数据类型 | 金额使用 `NUMERIC(18,2)`；业务时间使用 `TIMESTAMPTZ` |
| 业务时区 | `Asia/Shanghai`；从时间戳派生日期时明确该时区 |
| 主键 | ODS 交易用技术主键；DWD 交易用交易 ID；贷款快照用贷款 ID + 日期 |
| 批次和入仓时间 | 在 ODS 中保存 `batch_id`、`load_time`，支持质量检查和追溯 |
| 唯一性及约束 | 使用 `PRIMARY KEY`、`NOT NULL`、`UNIQUE`、`CHECK` 等保障表内基本质量 |
| 关联查询 | 必须预防一对多表直接 JOIN 造成重复行、重复求和 |
| 增量策略 | 需要提前在设计文档中说明，实际数据导入和 UPSERT 留到后续学习 |

**特别注意重复 JOIN：** 一份合同若有 3 笔放款和 5 笔还款，直接将两张明细表同时关联到贷款合同，可能产生 15 行组合，造成重复求和。应先分别按 `loan_id` 汇总放款与还款，再关联结果。

## 6. 今日交付物与检查

主要设计文件：

```text
docs/layer_design.md
sql/ods/ddl.sql
sql/dwd/ddl.sql
```

建表后，可使用以下 SQL 检查三张表是否存在：

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('ods', 'dwd')
ORDER BY table_schema, table_name;
```

进一步核对字段：

```sql
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema IN ('ods', 'dwd')
ORDER BY table_schema, table_name, ordinal_position;
```

**当前完成情况：** 已学习各层职责、批次、粒度和主键设计，并基于 Source V1.1 字段字典重新整理分层文档与 DDL；**本地 PostgreSQL 建表执行及结构验收尚未在本次对话中确认**，需要实际运行 SQL 检查。

## 7. 今日总结

今天最大的收获不是 `CREATE TABLE` 语法，而是理解了数据仓库的整体设计逻辑：Source 承接业务事件，ODS 负责可靠接入和追溯，DWD 建立口径统一、粒度明确的明细事实，DWS 复用公共汇总结果，ADS 面向报表和其他应用提供数据。

同时认识到：同一业务 ID 在 ODS 中可能因不同批次多次出现；DWD 交易明细需要按业务 ID 去重；贷款日快照则允许同一贷款在不同日期出现，必须采用联合主键。业务时间与载入时间也必须区分，才能正确处理延迟数据。

**下一步（D09）：** 学习 Source → ODS → DWD 的实际数据加载、增量抽取、幂等重跑、去重及 `INSERT ... ON CONFLICT`（UPSERT）。
