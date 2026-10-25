# D06 SQL 基础业务查询学习总结

**学习主题：** PostgreSQL 基础业务查询与银行数据分析  
**学习项目：** bank-data-platform  
**学习日期：** 2026-10-24  
**学习内容：** JOIN、GROUP BY、HAVING、CTE、窗口函数、NULL 处理与重复 JOIN

---

## 一、今日学习目标

本次学习主要围绕银行业务数据展开，通过实际 SQL 查询，掌握多表关联、分组统计、复杂查询拆解和窗口函数的使用。

核心目标是能够根据业务需求，独立编写 SQL，并验证查询结果是否正确。

## 二、核心知识点

### 1. JOIN：多表关联

**作用：** 将不同业务表通过主键和外键关联起来。

常用关联方式：

- `INNER JOIN`：只保留两张表中匹配成功的记录。
- `LEFT JOIN`：保留左表全部记录，右表没有匹配时返回 NULL。

示例：

```sql
SELECT
    c.customer_id,
    a.account_id
FROM source.customers c
LEFT JOIN source.accounts a
    ON c.customer_id = a.customer_id;
```

查找没有开户的客户：

```sql
SELECT
    c.customer_id
FROM source.customers c
LEFT JOIN source.accounts a
    ON c.customer_id = a.customer_id
WHERE a.account_id IS NULL;
```

**学习收获：** 理解了 INNER JOIN 与 LEFT JOIN 的区别，以及通过 `IS NULL` 查找没有关联记录的数据。

### 2. GROUP BY：分组统计

**作用：** 按指定字段对数据分组，然后使用聚合函数进行统计。

常见聚合函数：

| 函数 | 作用 |
|---|---|
| SUM() | 求和 |
| COUNT() | 计数 |
| AVG() | 平均值 |
| MAX() | 最大值 |
| MIN() | 最小值 |

示例：统计每个账户的交易金额与交易笔数。

```sql
SELECT
    account_id,
    SUM(amount) AS total_amount,
    COUNT(*) AS transaction_count
FROM source.transactions
GROUP BY account_id;
```

**学习收获：** 理解了统计粒度的概念，即一行结果代表一个账户、一个客户还是一个地区，由 GROUP BY 的字段决定。

### 3. HAVING：筛选分组统计结果

**作用：** 对 GROUP BY 后的聚合结果进行筛选。

WHERE 和 HAVING 的区别：

| WHERE | HAVING |
|---|---|
| 筛选原始记录 | 筛选聚合结果 |
| 在分组之前执行 | 在分组之后执行 |
| 不能直接使用 SUM 等聚合函数 | 可以使用聚合函数 |

示例：查询交易金额超过 50000 元、交易笔数不少于 10 笔的账户。

```sql
SELECT
    account_id,
    SUM(amount) AS total_amount,
    COUNT(*) AS transaction_count
FROM source.transactions
GROUP BY account_id
HAVING SUM(amount) > 50000
   AND COUNT(*) >= 10;
```

**学习收获：** 明白了 WHERE 会先过滤原始数据，HAVING 则根据聚合结果进行筛选。

### 4. CTE：公共表表达式

**作用：** 使用 `WITH ... AS (...)` 将复杂 SQL 拆分成多个容易理解的查询步骤。

基本语法：

```sql
WITH summary AS (
    SELECT
        account_id,
        SUM(amount) AS total_amount
    FROM source.transactions
    GROUP BY account_id
)
SELECT *
FROM summary
WHERE total_amount > 50000;
```

多个 CTE 可以分别处理不同业务逻辑，最后通过 JOIN 关联。

在贷款业务中：

- 第一个 CTE 统计每笔贷款累计放款金额。
- 第二个 CTE 统计每笔贷款累计还款本金。
- 外层通过 loan_id 关联，计算未偿还本金。

**学习收获：** 掌握了将复杂业务拆分成多个查询步骤的方法，理解了先聚合、后关联可以减少重复计算风险。

### 5. 窗口函数：排名与时间序列分析

窗口函数的核心特点是：**在保留原始结果行的同时，增加排名、累计值等分析指标。**

#### （1）RANK()：排名

```sql
RANK() OVER (
    ORDER BY total_amount DESC
)
```

常见排名函数：

| 函数 | 相同金额时的排名 |
|---|---|
| ROW_NUMBER() | 1、2、3、4 |
| RANK() | 1、2、2、4 |
| DENSE_RANK() | 1、2、2、3 |

#### （2）PARTITION BY：划分窗口

```sql
RANK() OVER (
    PARTITION BY region
    ORDER BY total_amount DESC
)
```

作用是按照地区分别排名。

理解：

- `PARTITION BY`：决定和谁一起计算。
- `ORDER BY`：决定按照什么顺序计算。

#### （3）SUM() OVER()：累计求和

```sql
SUM(monthly_amount) OVER (
    ORDER BY month
    ROWS BETWEEN UNBOUNDED PRECEDING
             AND CURRENT ROW
)
```

作用是计算从第一行到当前行的累计金额。

例如：

| 月份 | 当月金额 | 累计金额 |
|---|---:|---:|
| 1 月 | 10000 | 10000 |
| 2 月 | 20000 | 30000 |
| 3 月 | 15000 | 45000 |

#### （4）LAG()：获取上一行的数据

```sql
LAG(monthly_amount, 1) OVER (
    ORDER BY month
)
```

可以用于计算月度环比增长率：

```sql
ROUND(
    (monthly_amount - previous_amount)
    * 100.0 / NULLIF(previous_amount, 0),
    2
) AS mom_growth_pct
```

需要注意，LAG 获取的是排序后的上一行，不一定是上一个自然月。

**学习收获：** 初步掌握了排名、地区分区排名、累计求和与环比增长率的计算方法。

### 6. NULL：空值处理

常用函数和语法：

| 语法 | 作用 |
|---|---|
| IS NULL | 判断是否为空 |
| IS NOT NULL | 判断是否非空 |
| COALESCE(x, 0) | x 为 NULL 时返回 0 |
| NULLIF(x, 0) | x 等于 0 时返回 NULL |

例如：

```sql
COALESCE(total_disbursed, 0)
-
COALESCE(total_repaid, 0)
AS outstanding_principal
```

通过 COALESCE 避免缺失的金额导致计算结果为 NULL。

需要根据业务含义决定是否把 NULL 转换为 0，不能认为所有 NULL 都等于 0。

### 7. 重复 JOIN：避免统计金额错误

当两张明细表存在一对多关系时，直接 JOIN 可能导致记录数量膨胀。

例如：

- 某笔贷款有 2 条放款记录。
- 同一笔贷款有 3 条还款记录。
- 直接按 loan_id JOIN，可能产生 2 × 3 = 6 条记录。

如果直接对 JOIN 后的数据执行 SUM，可能导致放款和还款金额重复累计。

正确思路：

1. 分别对放款和还款记录按照 loan_id 聚合。
2. 确保两个汇总结果中每笔贷款最多只有一行。
3. 再进行 JOIN。
4. 最后计算未偿还本金。

**学习收获：** 理解了 JOIN 可能造成的金额膨胀问题，掌握了通过预聚合降低重复计算风险的方法。

---

## 三、其他 SQL 语法补充

本次学习还涉及以下常用语法：

| 语法 | 作用 |
|---|---|
| DATE_TRUNC('month', date) | 将日期截断到月份 |
| EXTRACT(YEAR FROM date) | 提取年份 |
| IN (1, 2) | 判断是否属于指定集合 |
| DISTINCT | 去除重复值 |
| COUNT(DISTINCT id) | 统计不重复的编号数量 |
| ORDER BY ... DESC | 降序排列 |
| ORDER BY ... ASC | 升序排列 |
| ROUND(x, 2) | 保留两位小数 |
| ALTER TABLE | 修改已有表结构 |
| ADD COLUMN | 增加字段 |
| UPDATE ... SET | 修改数据 |
| RANDOM() | 生成随机数 |

日期筛选推荐使用左闭右开区间：

```sql
WHERE transaction_time >= '2026-01-01'
  AND transaction_time < '2027-01-01'
```

避免遗漏 2026 年 12 月 31 日当天包含时分秒的交易。

---

## 四、今日银行业务练习

| 业务题 | 训练内容 | 完成情况 |
|---|---|---|
| 客户账户关联 | INNER JOIN | 已完成 |
| 未开户客户查询 | LEFT JOIN + IS NULL | 已完成 |
| 账户交易统计 | GROUP BY + SUM + COUNT | 已完成 |
| 高交易额账户筛选 | HAVING | 已完成 |
| 贷款累计放款统计 | 单个 CTE | 已练习 |
| 贷款未偿还本金 | 多 CTE + JOIN + COALESCE | 已练习并修正 |
| 账户交易额排名 | RANK() | 已完成核心查询 |
| 地区客户交易额排名 | PARTITION BY | 已练习并发现分组问题 |
| 月度累计交易额 | SUM() OVER() | 已练习并修正窗口定义 |
| 月度环比分析 | LAG() + NULLIF() | 已练习并修正 |
| JOIN 重复检查 | JOIN + COUNT + HAVING | 已练习并发现关联条件错误 |
| 月度活跃客户统计 | COUNT(DISTINCT) | 待修正 SQL |
| 未结清贷款数量统计 | CTE + JOIN + COUNT + SUM | 待修正 SQL |

此外，为客户表新增了 `region` 字段，并为已有模拟客户填充地区数据，用于练习地区排名。

---

## 五、今日发现的问题

### 1. JOIN 条件容易写错

曾出现将同一张表的字段与自身比较，或者用账户编号错误关联客户编号的问题。

改进方法：在写 JOIN 前先明确主键、外键以及表之间的对应关系。

### 2. GROUP BY 统计粒度需要明确

如果业务要求统计客户交易金额，就应该按照 customer_id 聚合，而不是 account_id。

写 SQL 前需要先明确：**最终结果中的一行代表什么业务对象？**

### 3. PARTITION BY 和 ORDER BY 容易混淆

- PARTITION BY 用于划分独立的计算范围。
- ORDER BY 用于定义计算顺序。

例如计算所有月份的累计金额，只需要按月份排序，不应把每个月划分成独立分区。

### 4. NULL 处理需要完整

进行金额相减时，需要考虑放款金额和还款金额是否都可能为 NULL。

### 5. 需要严格遵守业务统计口径

不能随意增加业务需求中不存在的筛选条件。

例如，统计总交易额超过 50000 元的账户，不代表需要筛选单笔金额超过 5000 元的交易。

### 6. 容易遗漏输出规范

多次出现漏写最终 ORDER BY、字段别名不一致以及输出字段过多的问题。

后续需要逐条检查业务需求。

---

## 六、总结与后续计划

今天完成了 JOIN、GROUP BY、HAVING、CTE、窗口函数、NULL 处理和重复 JOIN 等 SQL 知识的系统学习。

通过银行业务案例，已经能够独立编写基本的多表关联、分组统计和窗口函数查询，并逐步理解业务统计粒度、数据关联关系和金额统计准确性的重要性。

目前仍需要进一步巩固复杂 SQL 的正确性检查，尤其是多表 JOIN、CTE 字段引用、NULL 处理和最终统计口径。

**后续需要完成的任务：**

- [ ] 修正月度活跃客户统计 SQL。
- [ ] 修正未结清贷款数量统计 SQL。
- [ ] 整理六项正式业务查询到 `sql/analysis/01_06.sql`。
- [ ] 使用数据库实际数据运行并检查查询结果。
- [ ] 使用手工样例验证关键金额及计数结果。
- [ ] 完成 D06 的最终代码提交。

**今日核心收获：SQL 不只是实现查询，更重要的是保证查询结果符合业务定义，并且不会因为关联、空值或统计粒度错误而产生不正确的数据。**