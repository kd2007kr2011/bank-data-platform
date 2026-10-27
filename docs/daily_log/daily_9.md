# D09 学习记录：全量抽取与装载

**学习日期：** 2026-10-27  
**项目：** 零售银行数据平台（bank-data-platform）  
**主题：** Source → ODS 全量抽取、分批装载、批次管理与事务控制

## 1. 今日学习目标

- 理解 ETL 中 Extract（抽取）和 Load（装载）的职责。
- 使用 Python、psycopg 和 PostgreSQL 游标读取源业务数据。
- 理解全量抽取与分批读取的区别，掌握 `fetchmany()` 和 `yield` 的作用。
- 实现 `source.transactions` 到 `ods.ods_transaction` 的数据装载。
- 学习 `batch_id`、`load_time`、`source_system` 等装载元数据，以及事务提交和回滚。
- 了解同批次重跑、不同批次保留历史和数据校验。

## 2. 对 Source → ODS 数据装载的理解

Source 保存原始业务数据，ODS 负责接入数据并记录装载来源、批次和时间。今天主要实现抽取与装载，不在这一环节进行复杂的业务清洗和汇总。

```text
source.transactions
       ↓
extract_full.py
  SELECT + 服务端 Cursor + fetchmany()
       ↓ 逐批交出数据
load_ods.py
  添加 batch_id / load_time / source_system
  分批 INSERT + 数据校验 + 事务控制
       ↓
ods.ods_transaction
```

**认识：** Extract 负责把数据读出来，Load 负责把数据可靠地写入 ODS；两者配合完成 Source → ODS 的 ETL 链路。

## 3. Extract：全量抽取与分批读取

### 3.1 全量抽取不等于一次性读取

当前任务是**全量抽取、分批读取**：抽取范围覆盖 `source.transactions` 的全部记录，但每次只取指定数量的记录。

例如 Source 有 10 万条记录，设置 `BATCH_SIZE = 1000`，程序会分多批处理，最终仍覆盖全部 10 万条，而不是只读取 1000 条。

- `fetchall()`：一次取回查询结果，数据量较大时可能占用较多内存。
- `fetchmany(1000)`：每次取最多 1000 条。
- 服务端 Cursor（`conn.cursor(name=...)`）：使结果可在服务端逐批读取，避免一般客户端游标可能存在的完整结果缓存问题。
- `yield`：将当前批次交给调用方，下一次迭代时继续抽取。

### 3.2 extract_full.py 的职责

```python
with conn.cursor(name="extract_transaction_cursor") as cur:
    cur.execute("SELECT * FROM source.transactions ORDER BY transaction_id")
    while True:
        rows = cur.fetchmany(1000)
        if not rows:
            break
        yield rows
```

实际项目代码使用明确的字段列表，而不是依赖 `SELECT *` 的列顺序。Extract 只负责读取，不直接修改 ODS，也不独立提交装载事务。

## 4. Load：ODS 装载程序

`etl/load_ods.py` 是装载流程的控制入口，主要负责：

1. 加载 `.env` 数据库配置，通过 `psycopg.connect()` 建立连接。
2. 使用代码顶部的 `BATCH_ID`、`BATCH_SIZE`、`SIMULATE_FAILURE` 配置运行参数。
3. 在事务中删除**当前 batch_id** 对应的旧 ODS 记录，而不删除其他批次。
4. 调用 `extract_transactions()` 分批获取 Source 数据。
5. 为每条记录附加 `batch_id`、`load_time`、`source_system`。
6. 使用 `cursor.executemany()` 批量插入 ODS。
7. 比较 Source 记录数、本次抽取记录数和本次 ODS 批次记录数。
8. 成功时提交事务，异常时回滚。

当前处理的 Source 字段为：`transaction_id`、`account_id`、`transaction_type`、`amount`、`transaction_status`、`transaction_time`、`created_at`。

对应 ODS 表为 `ods.ods_transaction`，额外保存 `ods_id`、`batch_id`、`load_time` 和 `source_system`。

## 5. 批次管理与幂等重跑

当前采用的是**按批次保存的全量快照**，而不是始终只保留一份最新数据。

| 执行场景 | 预期行为 |
|---|---|
| 首次执行 `batch_001` | 保存一份完整的全量快照 |
| 执行 `batch_002` | 保留 `batch_001`，新增另一个快照 |
| 再次执行 `batch_002` | 删除并重写 `batch_002`，不无限累积同批次重复交易 |
| `batch_002` 重跑失败 | 整个未提交的修改回滚，保留此前成功提交的版本 |

在 D08 的设计中，`ods_id` 是技术主键，`transaction_id` 是源业务主键，`UNIQUE(batch_id, transaction_id)` 保证**同一批次同一交易**最多保存一行；同一交易允许出现在不同批次。

要注意：同批次重新装载会产生新的 `load_time` 和可能不同的 `ods_id`，因此这里强调的是业务记录的幂等性，并非每个元数据字段都不变。

## 6. Connection、Cursor 与 Transaction

| 概念 | 作用 |
|---|---|
| Connection | 建立 Python 与 PostgreSQL 之间的数据库连接 |
| Cursor | 执行 SQL、读取查询结果或写入数据 |
| Transaction | 把一组数据库修改作为整体提交或回滚 |
| `COMMIT` | 确认并提交事务修改 |
| `ROLLBACK` | 撤销当前事务中尚未提交的修改 |

当前装载程序在同一连接和事务中执行删除、抽取、插入与校验，使用 `REPEATABLE READ` 获取一致性数据视图；连接上下文正常结束时提交，发生异常时回滚。设置的事务级 advisory lock 用于协调遵守同一锁规则的相同批次任务。

**认识：** Cursor 负责执行 SQL，Transaction 负责控制整组操作是否最终生效，两者不能混为一谈。

## 7. 数据校验与验收方法

### 7.1 对比 Source 与指定 ODS 批次记录数

```sql
SELECT COUNT(*) FROM source.transactions;

SELECT COUNT(*)
FROM ods.ods_transaction
WHERE batch_id = 'batch_20261026';
```

在源数据一致且没有过滤规则的情况下，两个数量应一致。

### 7.2 查看各批次记录数

```sql
SELECT batch_id, COUNT(*) AS row_count
FROM ods.ods_transaction
GROUP BY batch_id
ORDER BY batch_id;
```

### 7.3 检查同批次重复交易

```sql
SELECT batch_id, transaction_id, COUNT(*) AS duplicate_count
FROM ods.ods_transaction
GROUP BY batch_id, transaction_id
HAVING COUNT(*) > 1;
```

若唯一约束生效，正常情况下应无返回行。

### 7.4 测试失败回滚

将 `SIMULATE_FAILURE` 改为 `True`，让程序在装载过程中主动抛出异常；随后查询目标批次记录数，检查失败任务是否未留下部分提交结果。测试结束后恢复为 `False`。

**验收状态：** 已完成两个脚本的编写和启动参数调整；已确认装载程序可直接通过顶部配置运行。重复运行、历史批次和故障回滚三项验收的实际结果尚未在本次交流中逐项确认，不记录为已通过。

## 8. 今日遇到的问题

1. **Pylance 提示 `fetchone()` 可能返回 `None`**：先把结果保存到变量，检查 `result is None`，再读取 `result[0]`。
2. **运行时报缺少 `--batch-id`**：原版本用 `argparse` 将其设置为必填参数；后来改为在代码顶部统一配置 `BATCH_ID`，可以直接执行脚本。
3. **容易混淆全量抽取与分批读取**：`fetchmany()` 只是控制每次读取的数量，并不会把全量任务自动变成增量任务。

## 9. 今日总结

今天学习了 Source → ODS 的实际数据装载流程：Extract 使用 PostgreSQL 服务端游标、`fetchmany()` 和 `yield` 分批读取 Source；Load 建立数据库连接、为源数据增加批次元数据、批量写入 ODS，并进行记录数校验和事务控制。

当前采用**全量抽取 + 分批读取/写入 + 按批次保存历史快照**的方式。`batch_id` 用于区分装载批次，同一批次可以重跑替换；不同批次可以保留源业务记录在不同同步时间的状态。通过事务控制，尽量避免失败时留下不完整的批次。

最重要的三个认识是：

- **`fetchmany()` 解决高效、分批读取的问题。**
- **`batch_id` 解决数据批次管理与历史快照识别的问题。**
- **Transaction 解决装载过程中整体提交或回滚的问题。**

## 10. 下一步

- 实际完成同批次重跑、不同批次保留和异常回滚的验收，记录运行结果。
- 将交易表的 ETL 方式扩展到客户、账户、贷款、放款和还款表。
- 后续学习增量抽取、UPSERT、统一批次管理，以及 ODS → DWD 的去重和标准化加工。
