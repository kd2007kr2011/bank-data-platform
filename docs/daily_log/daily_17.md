# D17｜DWS 客户交易汇总

**学习日期：** 2026-11-11  
**学习主题：** DWS 客户与地区交易日汇总  
**核心目标：** 将 DWD 层的交易事实明细按照客户和地区进行聚合，形成可以重复使用的业务统计数据。

## 一、今日学习目标

今天主要学习 DWS（Data Warehouse Service，数据汇总层）的基本作用，以及如何利用 SQL 将 DWD 中的交易明细加工成不同维度的统计结果。

主要完成两个任务：

1. 创建客户交易日汇总表 `dws_customer_transaction_daily`。
2. 创建地区交易日汇总表 `dws_region_transaction_daily`。

## 二、DWS 层的作用

DWD 层主要保存清洗和标准化后的业务明细，一条记录代表一笔交易。

但在实际业务中，分析人员通常不需要每次都读取所有交易明细，而是希望直接获得已经统计好的业务数据。

例如：

- 某个客户每天发生了多少笔交易？
- 某个客户每天成功交易的金额是多少？
- 某个地区每天发生了多少笔交易？
- 不同地区的交易规模有什么区别？

因此，需要在 DWD 的基础上建立 DWS 层，提前完成常用的统计计算。

DWS 的核心作用是将明细数据按照业务分析需要进行汇总，提高数据的复用性，减少重复计算。

## 三、今日完成的任务

### 1. 客户交易日汇总

**目标表：** `dws.dws_customer_transaction_daily`

**数据来源：**
- `dwd.fact_transaction`
- `dwd.dim_date`

**数据粒度：** 一个客户在一天内一条记录。

主要统计三个指标：

| 字段 | 含义 | 计算方式 |
|---|---|---|
| total_transaction_count | 每日交易总笔数 | COUNT(*) |
| success_count | 每日成功交易笔数 | COUNT(*) FILTER |
| success_amount | 每日成功交易金额 | SUM(amount) FILTER |

核心 SQL：

```sql
INSERT INTO dws.dws_customer_transaction_daily (
    business_date,
    customer_key,
    total_transaction_count,
    success_count,
    success_amount
)
SELECT
    dd.full_date,
    ft.customer_key,
    COUNT(*),
    COUNT(*) FILTER (
        WHERE ft.transaction_status = 'SUCCESS'
    ),
    COALESCE(
        SUM(ft.amount) FILTER (
            WHERE ft.transaction_status = 'SUCCESS'
        ),
        0
    )
FROM dwd.fact_transaction ft
JOIN dwd.dim_date dd
    ON ft.date_key = dd.date_key
GROUP BY
    dd.full_date,
    ft.customer_key;
```

这里最重要的是 `GROUP BY`。

通过 `business_date + customer_key` 进行分组，将同一个客户在同一天发生的多笔交易合并为一条记录。

### 2. 地区交易日汇总

**目标表：** `dws.dws_region_transaction_daily`

**数据来源：**
- `dwd.fact_transaction`
- `dwd.dim_date`

**数据粒度：** 一个地区在一天内一条记录。

统计指标与客户汇总表保持一致：

| 字段 | 含义 |
|---|---|
| total_transaction_count | 每日交易总笔数 |
| success_count | 每日成功交易笔数 |
| success_amount | 每日成功交易总金额 |

核心 SQL：

```sql
INSERT INTO dws.dws_region_transaction_daily (
    business_date,
    region_key,
    total_transaction_count,
    success_count,
    success_amount
)
SELECT
    dd.full_date,
    ft.region_key,
    COUNT(*),
    COUNT(*) FILTER (
        WHERE ft.transaction_status = 'SUCCESS'
    ),
    COALESCE(
        SUM(ft.amount) FILTER (
            WHERE ft.transaction_status = 'SUCCESS'
        ),
        0
    )
FROM dwd.fact_transaction ft
JOIN dwd.dim_date dd
    ON ft.date_key = dd.date_key
GROUP BY
    dd.full_date,
    ft.region_key;
```

与客户汇总不同，这里使用 `region_key` 作为分组维度。

即将同一个地区在同一天发生的所有客户交易合并，得到地区每日交易统计结果。

对于 `region_key` 为空的记录，保留为未知地区的独立统计分组，避免数据遗漏。

## 四、今日学习的 SQL 知识

### 1. GROUP BY 分组聚合

`GROUP BY` 是今天最重要的知识。

它能够按照指定字段对数据进行分组，然后对每个分组分别进行统计。

例如：

```sql
GROUP BY business_date, customer_key
```

表示按照日期和客户进行分组。

而：

```sql
GROUP BY business_date, region_key
```

表示按照日期和地区进行分组。

改变分组字段，就能够从不同维度观察同一批交易数据。

### 2. COUNT(*) 统计数量

```sql
COUNT(*)
```

统计当前分组中的全部交易记录数量。

### 3. FILTER 条件统计

```sql
COUNT(*) FILTER (
    WHERE transaction_status = 'SUCCESS'
)
```

只统计交易状态为 SUCCESS 的记录。

相比单独编写多个查询，FILTER 可以在一次分组计算中完成不同条件的统计。

### 4. SUM 金额汇总

```sql
SUM(amount) FILTER (
    WHERE transaction_status = 'SUCCESS'
)
```

只计算成功交易的金额总和。

### 5. COALESCE 空值处理

```sql
COALESCE(SUM(amount), 0)
```

当没有符合条件的交易时，SUM 可能返回 NULL，使用 COALESCE 将其转换为 0。

## 五、数据处理流程

今天完成后，项目的数据处理流程进一步完善：

```text
Source
  ↓
ODS
  ↓
DWD
  ├── 交易明细
  ├── 贷款明细
  ├── 客户维度
  ├── 地区维度
  └── 日期维度
  ↓
DWS
  ├── 客户每日交易汇总
  └── 地区每日交易汇总
  ↓
ADS
  └── 后续业务指标与分析应用
```

DWD 主要解决数据清洗、标准化和事实建模的问题。

DWS 则在 DWD 的基础上，按照不同业务维度提前完成数据聚合，为后续分析提供可复用的数据。

## 六、数据校验

完成汇总后，需要验证 DWS 数据是否与 DWD 一致。

主要检查：

1. 客户日汇总的交易笔数总和是否等于 DWD 交易总数。
2. 地区日汇总的交易笔数总和是否等于 DWD 交易总数。
3. 客户日汇总与地区日汇总的交易笔数是否一致。
4. 成功交易金额在不同汇总表之间是否一致。
5. 随机抽取 10 个客户，重新从 DWD 计算每日交易笔数和金额，与 DWS 结果进行比较。

通过这些检查，确认数据聚合过程中没有出现重复统计或数据遗漏。

## 七、今日学习总结

今天主要学习了如何将 DWD 中的一笔笔交易明细，转换成按照客户和地区组织的每日汇总数据。

具体实现上，主要是编写 SQL，通过 JOIN 关联日期维度表，再使用 GROUP BY 确定统计粒度，最后使用 COUNT、SUM、FILTER 等聚合函数计算业务指标，并将结果写入 DWS 表。

今天最重要的收获是理解了数据粒度和聚合维度的关系。

同一份交易明细数据，可以按照客户进行汇总，也可以按照地区进行汇总。只需要改变 GROUP BY 的字段，就能得到不同业务视角下的统计结果。

从实际工作来看，数据开发人员需要根据业务部门的分析需求，设计合理的汇总表，将常用的统计指标提前加工好，并通过规范的数据处理和校验流程，向其他分析人员提供稳定、可复用的数据。

**今日核心认识：DWD 关注每一笔交易发生了什么，DWS 关注每个客户、每个地区每天发生了什么。**

## 八、今日交付

| 文件 | 交付内容 |
|---|---|
| `sql/dws/customer_daily.sql` | 客户交易日汇总 |
| `sql/dws/region_daily.sql` | 地区交易日汇总 |
| DWS 客户汇总表 | `dws.dws_customer_transaction_daily` |
| DWS 地区汇总表 | `dws.dws_region_transaction_daily` |
| 数据校验 SQL | DWD 与 DWS 汇总结果对账 |

**D17 学习完成。**