# D12：DWD 交易明细清洗

## 一、学习目标

将 ODS 层的交易数据转换为规范、可追溯、可重复执行的 DWD 交易明细数据。

本日重点学习：

-   DWD 事实表粒度与业务主键
-   使用 `ROW_NUMBER()` 进行业务键去重
-   交易类型、交易状态和金额的规范化检查
-   使用 `ON CONFLICT` 实现插入或更新
-   使用数据库事务保证失败回滚
-   对账统计与幂等性验证

## 二、数据处理流程

``` text
ods.transaction_current
        |
        v
读取 ODS 交易记录
        |
        v
ROW_NUMBER() 按 transaction_id 排序
        |
        v
字段合法性与业务规则检查
        |
        +----------------------+
        |                      |
        v                      v
有效候选记录                拒收记录
        |                      |
        v                      v
写入/更新 DWD             ods.rejected_records
        |
        v
对账与质量检查
        |
        v
提交事务
```

ODS 主要负责保存来源数据及装载追溯信息；DWD
负责形成规范的业务事实记录。当前 DWD
交易明细表采用"一笔交易一行"的粒度，以 `transaction_id` 作为业务主键。

## 三、检查 ODS 和 DWD 表结构

开发前检查了 ODS 与 DWD
的字段、数据类型、主键和约束，明确了主要字段映射。

  DWD 字段               来源或处理方式                      作用
  ---------------------- ----------------------------------- ----------------
  `transaction_id`       ODS `transaction_id`                交易业务主键
  `account_id`           ODS `account_id`                    账户标识
  `transaction_type`     ODS `transaction_type`              交易类型
  `amount`               转换为 `NUMERIC(18,2)`              交易金额
  `transaction_status`   ODS `transaction_status`            交易状态
  `transaction_time`     ODS `transaction_time`              交易发生时间
  `transaction_date`     按 `Asia/Shanghai` 从交易时间派生   业务日期
  `source_created_at`    ODS `created_at`                    源系统创建时间
  `source_batch_id`      ODS `batch_id`                      来源批次
  `ods_load_time`        ODS `loaded_at`                     ODS 装载时间
  `source_updated_at`    ODS `updated_at`                    源系统更新时间
  `dw_load_time`         DWD 构建时生成                      DWD 装载时间

为支持来源版本比较，在 DWD 表中增加了 `source_updated_at TIMESTAMPTZ`
字段。

## 四、DWD 交易规范化 SQL

SQL 文件：

``` text
sql/dwd/transaction.sql
```

### 4.1 使用 ROW_NUMBER() 去重

``` sql
ROW_NUMBER() OVER (
    PARTITION BY t.transaction_id
    ORDER BY
        t.updated_at DESC NULLS LAST,
        t.loaded_at DESC NULLS LAST,
        t.batch_id DESC
) AS rn
```

含义：

-   `PARTITION BY transaction_id`：按交易业务键分组。
-   `ORDER BY updated_at DESC`：优先选择源系统更新时间较新的记录。
-   `loaded_at` 和 `batch_id`：作为后续排序条件。
-   `rn = 1`：保留每组排序后的第一条记录。

当前 `ods.transaction_current`
是按交易保存当前状态的表，因此本次运行没有发现重复交易键，`duplicate_count = 0`。保留窗口函数是为了明确去重规则，并为后续数据来源扩展提供处理逻辑。

### 4.2 数据质量检查

对以下字段和业务规则进行检查：

  检查项                 拒收条件
  ---------------------- ----------------------
  `transaction_id`       为空
  `account_id`           为空或账户不存在
  `amount`               为空或小于等于 0
  `transaction_type`     不属于允许的交易类型
  `transaction_status`   不属于允许的交易状态
  `transaction_time`     为空
  `created_at`           为空
  `updated_at`           为空
  `batch_id`             为空
  `loaded_at`            为空

允许的交易类型：

-   `DEPOSIT`
-   `WITHDRAWAL`
-   `TRANSFER`

允许的交易状态：

-   `PENDING`
-   `SUCCESS`
-   `FAILED`
-   `CANCELLED`
-   `REVERSED`

需要注意：失败、取消、待处理和冲正状态属于业务状态，不应仅因为交易没有成功就当作坏数据。

### 4.3 拒收记录

不符合 DWD 规范的数据写入：

``` text
ods.rejected_records
```

记录来源表、批次、来源记录键、原始数据、规则代码、拒收原因和记录哈希。

使用：

``` sql
ON CONFLICT (source_table, record_hash, rule_code)
DO NOTHING
```

避免相同异常记录重复执行时不断新增拒收记录。

### 4.4 写入 DWD 与版本控制

使用：

``` sql
ON CONFLICT (transaction_id)
DO UPDATE SET ...
```

实现业务键冲突时更新已有记录。

通过来源更新时间控制是否允许覆盖：

``` sql
WHERE
    dwd.dwd_transaction_detail.source_updated_at IS NULL
    OR EXCLUDED.source_updated_at >
       dwd.dwd_transaction_detail.source_updated_at
```

这样，较新的来源版本可以更新 DWD，较旧或相同版本不会覆盖现有记录。

## 五、Python 构建脚本

脚本文件：

``` text
etl/dwd/build_dwd_transactions.py
```

主要职责：

1.  读取项目根目录下的 `.env` 配置。
2.  使用 `psycopg` 连接 PostgreSQL。
3.  读取 `sql/dwd/transaction.sql`。
4.  在数据库事务中执行数据转换。
5.  获取 SQL 返回的对账指标。
6.  检查来源记录是否能够对账。
7.  检查 DWD 业务键是否唯一。
8.  检查 DWD 金额、交易类型和交易状态。
9.  全部检查通过后提交事务；发生异常时回滚。

数据库连接使用上下文管理：

``` python
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(sql_text)
```

正常退出时提交事务，异常退出时回滚事务。

## 六、对账与幂等验证

### 6.1 对账指标

SQL 返回以下指标：

  指标                     含义
  ------------------------ --------------------------------
  `source_count`           本次读取的 ODS 来源记录数
  `duplicate_count`        去重淘汰的记录数
  `invalid_count`          质量检查不通过的记录数
  `eligible_count`         通过检查并进入写入流程的记录数
  `newly_rejected_count`   本次实际新增的拒收记录数
  `dwd_changed_count`      DWD 本次实际插入或更新的记录数

来源记录对账关系：

``` text
source_count = duplicate_count + invalid_count + eligible_count
```

注意，`eligible_count` 是有效候选记录数，不等于 DWD
净新增行数。已有业务键可能被更新，也可能因为来源版本未变化而不发生写入。

### 6.2 第一次执行结果

2026-10-30 第一次执行：

  指标                 结果
  ---------------- --------
  来源记录数         15,467
  重复淘汰记录数          0
  质量拒收记录数          0
  有效候选记录数     15,467
  新增拒收记录数          0
  DWD 实际变更数     15,467

对账关系：

``` text
15467 = 0 + 0 + 15467
```

说明本次读取的 15,467 条记录全部通过检查，并完成首次写入。

### 6.3 第二次执行结果

使用相同输入再次执行：

  指标                 结果
  ---------------- --------
  来源记录数         15,467
  重复淘汰记录数          0
  质量拒收记录数          0
  有效候选记录数     15,467
  新增拒收记录数          0
  DWD 实际变更数          0

第二次执行时，来源版本没有变化，因此 `ON CONFLICT ... DO UPDATE WHERE`
不再更新记录。

这证明相同输入重复执行不会产生额外的业务数据变更，幂等性验证通过。

### 6.4 数据库检查

检查 DWD 记录数：

``` sql
SELECT COUNT(*)
FROM dwd.dwd_transaction_detail;
```

检查业务键唯一性：

``` sql
SELECT
    transaction_id,
    COUNT(*)
FROM dwd.dwd_transaction_detail
GROUP BY transaction_id
HAVING COUNT(*) > 1;
```

检查交易状态分布：

``` sql
SELECT
    transaction_status,
    COUNT(*) AS cnt
FROM dwd.dwd_transaction_detail
GROUP BY transaction_status;
```

## 七、开发过程中遇到的问题及解决

### 问题一：交易类型 CHECK 约束拼写错误

报错：

``` text
违反检查约束 ck_dwd_transaction_type
```

排查后发现 DWD 约束中将 `WITHDRAWAL` 错写为 `WITHHDRAWAL`。

修复方式：删除错误约束，并重新创建包含正确枚举值的 CHECK 约束。

### 问题二：DWD 缺少 source_updated_at 字段

报错：

``` text
关系 dwd_transaction_detail 的 source_updated_at 字段不存在
```

原因：SQL 已经使用来源更新时间进行版本比较，但 DWD
表结构尚未增加该字段。

修复：

``` sql
ALTER TABLE dwd.dwd_transaction_detail
ADD COLUMN IF NOT EXISTS source_updated_at TIMESTAMPTZ;
```

### 问题三：确认交易类型数据是否异常

通过检查字符长度、字节长度、十六进制值和枚举匹配，确认 ODS 中只有：

-   `DEPOSIT`
-   `TRANSFER`
-   `WITHDRAWAL`

三种类型，均符合业务规则。最终定位到问题是 DWD 约束拼写错误，而不是 ODS
数据异常。

## 八、项目文件交付

``` text
bank-data-platform/
├── etl/
│   └── dwd/
│       └── build_dwd_transactions.py
│
└── sql/
    └── dwd/
        └── transaction.sql
```

本日完成的交付：

-   `sql/dwd/transaction.sql`
-   `etl/dwd/build_dwd_transactions.py`
-   DWD 表结构调整
-   首次构建及重复执行验证

## 九、今日学习总结

D12 完成了 ODS 到 DWD 的交易明细规范化处理。

通过本次开发，理解了 DWD 事实表的业务粒度，掌握了 `ROW_NUMBER()`
去重、数据质量检查、交易类型枚举约束、`NUMERIC` 金额精度、`ON CONFLICT`
UPSERT 和数据库事务管理。

同时，通过两次实际运行验证了数据对账和幂等性：首次成功处理 15,467
条交易，第二次重复执行时实际变更数为 0。

至此，完成了 Source → ODS → DWD 交易数据处理链路。

## 十、下一步学习计划：D13

主题：贷款与还款 DWD。

重点学习：

1.  贷款合同事实表设计。
2.  放款事件和还款事件的记录方式。
3.  累计放款本金计算。
4.  累计归还本金计算。
5.  贷款剩余本金计算。
6.  贷款每日快照构建与验证。
