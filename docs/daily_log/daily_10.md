# D10 学习记录：增量水位线与 ETL 增量同步

**项目：** Bank Data Platform  
**日期：** 2026-10-28  
**阶段：** 第 2 周 · 周 3  
**主题：** Watermark、Overlap Window、增量抽取与幂等装载

## 一、今日学习目标

在 D09 全量抽取与装载的基础上，实现 Source → ODS 的增量同步：只处理新增或发生变化的记录，通过元数据记录同步进度，避免重复数据，并保证任务失败时不错误推进水位线。

## 二、核心知识点

### 1. 全量同步与增量同步

- **全量同步（D09）：** 按批次抽取 Source 中符合范围的全部记录并装载到 ODS。
- **增量同步（D10）：** 依据上次同步进度和数据更新时间，仅抽取指定时间窗口内新增或更新的记录。
- 两者都有 Extract 和 Load 步骤；增量同步在此基础上增加了**水位线管理、重叠窗口、幂等装载及运行状态记录**。

### 2. 三个时间字段

| 字段 | 含义 | 主要作用 |
|---|---|---|
| `transaction_time` | 交易实际发生的业务时间 | 业务分析和报表日期归属 |
| `created_at` | Source 记录创建时间 | 判断记录何时创建 |
| `updated_at` | Source 记录最后更新时间 | 发现新增和已存在记录的变化 |

原先 `source.transactions` 没有 `updated_at`。今天通过数据库迁移增加该字段，并创建 PostgreSQL Trigger，在更新记录时自动维护 `updated_at`。

> 注意：`DEFAULT CURRENT_TIMESTAMP` 只处理插入时的默认值，不会自动随 `UPDATE` 改变，因此需要触发器或应用程序维护。给既有记录回填的时间也不一定代表其真实历史更新时间。

### 3. 元数据表与水位线（Watermark）

创建 `metadata.etl_runs`，记录每次任务的运行情况，包括 `run_id`、`job_name`、`status`、`watermark_start`、`watermark_end`、抽取/装载行数及错误信息。

每次增量同步先查找**上一次成功任务的 `watermark_end`**，作为本次同步的基准。任务只有在 ODS 装载成功后，才能将本次结束边界记录为新的成功水位线；失败时不得推进。

水位线代表**已成功处理的时间边界**，不是数据条数。即使某次没有新增数据，也可以在成功完成处理后推进水位线。

### 4. 重叠窗口（Overlap Window）

为减少边界附近数据因延迟可见而遗漏的风险，在上一次成功水位线基础上向前回退一定时间，例如 5 分钟。

示例：

- 上次成功水位线：10:00
- 重叠窗口：5 分钟
- 本次抽取起点：09:55
- 本次固定结束边界：11:00

增量抽取条件：

```sql
WHERE updated_at >= :start_time
  AND updated_at < :end_time
```

重叠窗口会让部分记录被重复抽取，因此需要在装载时去重。固定时间窗口**不能保证**捕获所有超长延迟或并发提交后才可见的数据，后续仍需考虑补偿、对账或 CDC。

### 5. 增量抽取（Extract）

在 `etl/extract_incremental.py` 中：

1. 连接 `bank_dev` 数据库。
2. 查询 `metadata.etl_runs` 中最近一次成功水位线。
3. 计算本次抽取的起止时间（含 overlap）。
4. 从 `source.transactions` 按 `updated_at` 查询记录。
5. 使用服务端游标与 `fetchmany()` 分批读取，并用 `yield` 逐批交给装载模块。

抽取模块只负责读取数据，不能单独宣布本次同步成功。

### 6. 增量装载（Load）与幂等性

在 `etl/load_incremental.py` 中，将抽取结果写入 ODS 最新状态表，使用：

```sql
INSERT INTO ods.transaction_current (...)
VALUES (...)
ON CONFLICT (transaction_id)
DO UPDATE SET ...
WHERE EXCLUDED.updated_at > ods.transaction_current.updated_at;
```

主要含义：

- 新的 `transaction_id`：插入。
- 已存在且来源版本更新：更新最新状态。
- 相同或更旧版本：跳过，避免重复变更。

**幂等性**：同样的数据重复执行装载，最终业务数据状态应保持一致。

`ods.transaction_current` 是按 `transaction_id` 保存**最新状态**的表；它并不代替需要保留全部交易变更、冲正事实的历史记录表。

### 7. 运行状态与事务

一次 ETL 任务大致经过：

```text
读取成功 Watermark
        ↓
确定 [start_time, end_time)
        ↓
创建 RUNNING 记录
        ↓
Extract：分批抽取
        ↓
Load：幂等写入 ODS
        ↓
全部成功 → 提交数据和 SUCCESS 水位线
发生异常 → 回滚未提交装载、记录 FAILED
```

关键原则：**不能先更新成功水位线，再装载 ODS。** 否则一旦装载失败，可能导致后续同步跳过尚未写入的数据。

## 三、今日完成的开发工作

| 文件或对象 | 完成内容 |
|---|---|
| `source.transactions.updated_at` | 增加最后更新时间字段 |
| Source 更新触发器 | 在交易记录发生更新时维护 `updated_at` |
| `metadata.etl_runs` | 保存 ETL 批次状态和同步水位线 |
| `etl/extract_incremental.py` | 读取水位线、计算重叠窗口、批量抽取 |
| `etl/load_incremental.py` | 分批装载、业务键去重、事务与运行状态处理 |
| `ods.transaction_current` | 保存每笔交易的最新状态 |

## 四、验收情况

本日已运行并验收增量同步流程，主要检查：

- 增量抽取和装载能够正常执行。
- 重复抽取不会在最新状态表中生成重复 `transaction_id`。
- 已存在交易的更新能够按 `updated_at` 同步。
- 成功任务记录对应的 Watermark；失败任务不能推进成功水位线。
- 边界数据按设定重叠窗口参与重复抽取与幂等处理。

> 本次属于学习项目的功能验收；极端并发、长时间迟到数据、进程崩溃恢复等生产级场景还需要更严格的测试。

## 五、今日总结

今天主要学习了 **ETL 增量同步**。与昨天 D09 的全量同步相比，Extract 和 Load 的基本结构没有改变，但增加了**元数据表、水位线和重叠窗口**。

每次同步时，先从 `metadata.etl_runs` 获取上一次成功同步的时间边界，再通过 overlap 往前回退一段时间，根据 `updated_at` 抽取新增或变化的数据。随后使用 `ON CONFLICT` 将数据幂等写入 ODS，只有装载成功后才推进水位线。

理解了以下关系：

- **D09：** 解决“如何把 Source 数据批量搬到 ODS”。
- **D10：** 解决“如何持续同步 Source 中新增或变化的数据，并管理同步进度”。

**核心收获：水位线负责记录进度，重叠窗口降低漏数风险，幂等装载处理重复数据，事务与任务状态保证同步成功后才推进进度。**

## 六、后续待深入的问题

1. 使用 CDC 捕获更严格的变更顺序，解决固定 overlap 无法覆盖的延迟提交问题。
2. 设计保留完整变更历史的 ODS 表，与最新状态表区分。
3. 增加同一任务的并发运行控制、异常恢复和数据对账。
4. 继续从 ODS 向 DWD 进行清洗、标准化与原子事实建模。
