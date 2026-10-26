# D08 数据仓库分层与字段映射设计

- 项目：零售银行数据平台
- 数据库：PostgreSQL
- 版本：D08 V1.2（基于用户提供的 `docs/data_dictionary.md` V1.1）
- 时区：`Asia/Shanghai`；金额：`NUMERIC(18,2)`，默认 CNY
- 范围：Source、ODS、DWD；本阶段创建三张表，非完整银行生产数仓

> **核对边界**：本设计逐字段核对了上传的 **Source V1.1 字段字典**，没有直接连入本地 PostgreSQL，也没有拿到 `sql/001_schema.sql` 的真实内容。执行前请用 `sql/checks/01_structure_checks.sql` 对照真实数据库。尤其是 schema、字段、状态和主键约束。

## 1. 三层的业务职责

| 层 | 主要职责 | 本项目现有/新增表 | 数据是否变换 |
|---|---|---|---|
| Source | 业务系统事实与事件的原始记录，维护业务约束 | `source.customers/accounts/transactions/loans/loan_disbursements/loan_repayments` | 业务系统负责维护 |
| ODS | 按装载批次记录源交易的落地副本，保留源字段及来源信息，便于溯源/重跑 | `ods.ods_transaction` | 尽量不改变源业务字段 |
| DWD | 统一业务口径、去重；以明确粒度存放可分析数据 | `dwd.dwd_transaction_detail`, `dwd.dwd_loan_snapshot` | 标准化、日期派生、按业务日计算 |

流程：

```text
source.transactions
      ↓ 按批次抽取（附 batch_id/load_time/source_system）
ods.ods_transaction
      ↓ 选择每笔交易采用的版本 + 派生 transaction_date
dwd.dwd_transaction_detail

source.loans + source.loan_disbursements + source.loan_repayments
      ↓ 截至指定业务日期，按贷款分别聚合成功放款/成功还本
 dwd.dwd_loan_snapshot
```

**边界说明**：D08 只设计一个交易 ODS 表。贷款日快照示例为了与当前表数量要求保持一致，直接读取三张贷款 Source 表；这是一种教学简化。在更完整的数仓中，通常也会先为贷款、放款和还款建立独立 ODS/DWD 明细，再生成快照。

## 2. Source 真实字段口径（据上传的 V1.1 字典）

- `source.transactions`：`transaction_id BIGINT`、`account_id BIGINT`、`transaction_type VARCHAR(20)`、`amount NUMERIC(18,2)`、`transaction_status VARCHAR(20)`、`transaction_time TIMESTAMPTZ`、`created_at TIMESTAMPTZ`。
  - 交易类型：`DEPOSIT`, `WITHDRAWAL`, `TRANSFER`。
  - 状态：`PENDING`, `SUCCESS`, `FAILED`, `CANCELLED`, **`REVERSED`**。
- `source.loans`：`loan_id`、`customer_id`、`contract_amount`、`loan_status`、`contract_date`、`created_at`。
  - 合同状态：`PENDING`, `ACTIVE`, `PAID_OFF`, `CANCELLED`。
- `source.loan_disbursements`：`disbursement_id`、`loan_id`、`disbursement_amount`、`disbursement_status`、`disbursement_time`、`created_at`。
  - 仅 `disbursement_status = 'SUCCESS'` 计入累计已放款。
- `source.loan_repayments`：`repayment_id`、`loan_id`、`principal_amount`、`interest_amount`、`repayment_status`、`repayment_time`、`created_at`。
  - 仅 `repayment_status = 'SUCCESS'` 的 `principal_amount` 计入累计已归还本金；利息 **不抵扣本金余额**。

## 3. 三张新表的粒度、主键、时间与增量策略

| 目标表 | 一行的含义（粒度） | 主键/唯一键 | 重要时间字段 | 增量/更新策略 |
|---|---|---|---|---|
| `ods.ods_transaction` | 一个批次中的一笔 Source 交易记录 | 技术 PK `ods_id`；`UNIQUE(batch_id, transaction_id)` | 源 `transaction_time`, `created_at`；仓库 `load_time` | 按批次追加；同批次重跑去重；不同批次可保留同交易 ID |
| `dwd.dwd_transaction_detail` | 一笔交易当前选用的标准记录 | `transaction_id` | `transaction_time`, `transaction_date`, `source_created_at`, `ods_load_time`, `dw_load_time` | 根据 ODS 中采用的最新记录 UPSERT；不得简单 `SUM` ODS 全部批次 |
| `dwd.dwd_loan_snapshot` | 一笔贷款在某个业务日截至日末的累计本金状态 | `(loan_id, snapshot_date)` | `contract_date`, `snapshot_date`, `dw_load_time` | 每日计算当日状态并 UPSERT；迟到数据需要重算受影响的历史业务日 |

### 为什么 ODS 要用批次？

数据同步可能每天运行，也可能手动补跑。`batch_id` 标识一次装载任务，`load_time` 表示进入 ODS 的实际时间。若 `transaction_id=10001` 分别在 `batch_A` 和 `batch_B` 导入，这两行可以共存，用于审计。

注意：当前 `UNIQUE(batch_id, transaction_id)` 假设**一个批次内同一交易只有一个版本**。若以后采用 CDC 流式变更，同批次可出现多个变更事件，就需要改成 `(batch_id, source_event_id)` 等版本粒度。

### 为什么快照按天增长？

快照记录的是**状态**，不是新的贷款合同。例如 loan_id=5 的 10 月 24、25、26 日状态是三行。因此主键必须同时包含 `loan_id` 与 `snapshot_date`。一万笔贷款、连续 365 天记录，会产生约 365 万行（是否纳入结清贷款由归档/快照范围策略决定）。后续可按日期分区和归档。

## 4. ODS 交易表字段设计（含映射）

| ODS 字段 | 数据类型 | 来源 | 映射或处理 |
|---|---|---|---|
| `ods_id` | BIGINT IDENTITY | ODS 生成 | 技术主键，不是交易 ID |
| `transaction_id` | BIGINT | `source.transactions.transaction_id` | 原样保留 |
| `account_id` | BIGINT | `source.transactions.account_id` | 原样保留 |
| `transaction_type` | VARCHAR(20) | `source.transactions.transaction_type` | 原样保留 |
| `amount` | NUMERIC(18,2) | `source.transactions.amount` | 原样保留 |
| `transaction_status` | VARCHAR(20) | `source.transactions.transaction_status` | 原样保留，包括 `REVERSED` |
| `transaction_time` | TIMESTAMPTZ | `source.transactions.transaction_time` | 原样保留业务时间 |
| `created_at` | TIMESTAMPTZ | `source.transactions.created_at` | 原样保留源记录创建时间 |
| `batch_id` | VARCHAR(100) | 装载任务 | 哪一次装载 |
| `load_time` | TIMESTAMPTZ | 数据库当前时间 | 进入 ODS 的时间 |
| `source_system` | VARCHAR(50) | 装载任务 | 本项目示例设为 `bank_core`（**新约定，不是 Source 字段**） |

ODS 不对源交易施加新的业务 CHECK；更严谨的原始保真如果要容纳字段缺失/非法值，应建立额外原始文本暂存或隔离区。这里基于 V1.1 的非空数据类型做简化设计。

## 5. DWD 交易明细字段设计与映射

| DWD 字段 | 来源 | 变换 |
|---|---|---|
| `transaction_id` | ODS 同名字段 | 每笔交易去重，作为 PK |
| `account_id` | ODS 同名字段 | 直接映射 |
| `transaction_type` | ODS 同名字段 | 校验 `DEPOSIT/WITHDRAWAL/TRANSFER` |
| `amount` | ODS 同名字段 | 数值保持不变，校验 > 0 |
| `transaction_status` | ODS 同名字段 | 校验五种合法状态，包括 `REVERSED` |
| `transaction_time` | ODS 同名字段 | 保留原业务时间 |
| `transaction_date` | `transaction_time` | `(transaction_time AT TIME ZONE 'Asia/Shanghai')::date` |
| `source_created_at` | `ods.created_at` | 重命名，明确来自源表 |
| `ods_id` | `ods.ods_id` | 审计追溯 |
| `source_batch_id` | `ods.batch_id` | 审计追溯 |
| `ods_load_time` | `ods.load_time` | 记录 ODS 装载时间 |
| `dw_load_time` | DWD 当前时间 | 记录该 DWD 记录写入/更新的时间 |

示例的“最新”规则是 `(load_time DESC, ods_id DESC)`。**这个规则仅适合当前演示**：当源系统存在晚到、重发、回滚变更时，装载时间不必然等于业务记录版本，应优先使用源系统的 `updated_at`、CDC LSN、版本号等。当前 Source V1.1 没有 `updated_at` 字段，因此不能假定具备完全正确的增量变更识别能力。

## 6. DWD 贷款日快照字段设计与映射

| 快照字段 | 来源 | 计算逻辑 |
|---|---|---|
| `loan_id` | `source.loans.loan_id` | 同名映射 |
| `snapshot_date` | 任务输入 | 快照业务日（中国时区） |
| `customer_id` | `source.loans.customer_id` | 同名映射 |
| `contract_date` | `source.loans.contract_date` | 同名映射 |
| `contract_amount` | `source.loans.contract_amount` | 合同金额，不等于实际放款 |
| `total_disbursed` | `source.loan_disbursements` | 对该贷款、业务日 <= 快照日、状态为 `SUCCESS` 的 `disbursement_amount` 求和 |
| `total_principal_repaid` | `source.loan_repayments` | 对该贷款、业务日 <= 快照日、状态为 `SUCCESS` 的 `principal_amount` 求和 |
| `outstanding_principal` | 以上两列 | PostgreSQL `GENERATED ALWAYS AS (total_disbursed - total_principal_repaid) STORED` |
| `dw_load_time` | DWD 当前时间 | 快照写入/重算时间 |

**有意不放入 `loan_status`**：Source V1.1 的 `source.loans.loan_status` 是当前合同状态，不是任意历史日的状态。直接写入 2026-01-01 的快照，会有“用今天状态假装历史状态”的风险。如未来需要“日末合同状态”，必须具备状态变更历史或事件日志。

**事件时间限制**：V1.1 中 `repayment_time` 是还款业务事件时间，不一定为成功入账时间。这里按业务时间截止、当前行状态为 SUCCESS 计算，适合课程演示，不能保证重建真实历史“当时已知”的余额。回溯历史时如果源记录被修改，还可能产生前视偏差。

**不重复求和**：分别将放款和还款按 `loan_id` 聚合后，再 LEFT JOIN 到 `source.loans`。不能先直接把一对多的放款记录和一对多的还款记录同时 JOIN，再 SUM；那会发生笛卡尔倍增。

## 7. 文件与执行顺序

```text
bank-data-platform/
├── docs/layer_design.md
├── sql/ods/ddl.sql
├── sql/dwd/ddl.sql
├── sql/etl/01_load_ods_transaction_example.sql
├── sql/etl/02_load_dwd_transaction.sql
├── sql/etl/03_build_loan_snapshot_example.sql
└── sql/checks/01_structure_checks.sql
```

推荐在项目根目录执行（根据本机实际用户名和数据库调整）：

```powershell
psql -h localhost -U postgres -d bank_dev -v ON_ERROR_STOP=1 -f sql/ods/ddl.sql
psql -h localhost -U postgres -d bank_dev -v ON_ERROR_STOP=1 -f sql/dwd/ddl.sql
psql -h localhost -U postgres -d bank_dev -v ON_ERROR_STOP=1 -f sql/checks/01_structure_checks.sql
```

**以上三条是 D08 必做**；只建结构，不自动装载。

可选 ETL 演示（先核对 Source 真实结构并完成 DDL）：

```powershell
psql -h localhost -U postgres -d bank_dev -v ON_ERROR_STOP=1 -v batch_id=batch_demo_001 -f sql/etl/01_load_ods_transaction_example.sql
psql -h localhost -U postgres -d bank_dev -v ON_ERROR_STOP=1 -f sql/etl/02_load_dwd_transaction.sql
psql -h localhost -U postgres -d bank_dev -v ON_ERROR_STOP=1 -v snapshot_date=2026-10-26 -f sql/etl/03_build_loan_snapshot_example.sql
```

> 注意：此 ODS 示例是 **全量源表导入某个 batch**，不能把“每天使用新 batch 全量复制”当作正式增量同步方案。实际增量应设计源变更发现、批次水位、异常重跑与幂等处理。

## 8. 验收标准与不包含的功能

- 三张表存在，字段及类型与本设计一致。
- ODS 使用技术主键 + `(batch_id, transaction_id)` 唯一约束。
- DWD 交易记录含五种合法状态，业务日期按 Asia/Shanghai 派生。
- 贷款快照使用 `(loan_id, snapshot_date)` 联合主键，累计还本不包含利息。
- 业务日与源创建时间、ODS 载入时间、DWD 写入时间定义清晰。
- `sql/checks/01_structure_checks.sql` 能查到约束和列。

未包含：生产级 CDC、贷款状态历史、资金冲正的完整双边会计口径、分区归档、自动日调度、全量数据质量和历史可重现账务系统。这些属于后续迭代。
