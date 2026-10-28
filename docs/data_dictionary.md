# 零售银行数据平台：业务字段字典

**文件路径：** `docs/data_dictionary.md`  
**文档版本：** V1.2  
**数据库：** PostgreSQL  
**数据层级：** Source（源业务数据层）  
**对应建表文件：** `sql/source/001_schema.sql`  
**增量变更脚本：** `sql/source/004_add_customer_region.sql`、`sql/source/005_add_transactions_updated`

---

## 1. 文档说明

本文档用于定义零售银行数据平台中源业务表的字段结构、数据类型、完整性约束以及业务规则。

当前版本包含六张源业务表：

| 表名 | 中文名称 | 业务用途 |
|---|---|---|
| `source.customers` | 客户表 | 存储客户基本信息及状态 |
| `source.accounts` | 账户表 | 存储客户账户信息 |
| `source.transactions` | 交易表 | 记录账户交易流水 |
| `source.loans` | 贷款合同表 | 存储贷款合同及合同金额 |
| `source.loan_disbursements` | 实际放款表 | 记录贷款实际发放情况 |
| `source.loan_repayments` | 贷款还款表 | 记录贷款本金及利息还款情况 |

## 2. customers（客户表）

**表名：** `source.customers`

**业务说明：** 存储银行客户基本资料、客户类型、客户状态及开户日期。一个客户可以拥有多个账户和多笔贷款。

| 字段 | 数据类型 | 约束 | 业务含义 |
|---|---|---|---|
| customer_id | BIGINT | PK, IDENTITY | 客户内部唯一标识，自动生成 |
| customer_name | VARCHAR(100) | NOT NULL | 客户姓名或企业名称 |
| customer_type | VARCHAR(20) | NOT NULL, CHECK | 客户类型 |
| customer_status | VARCHAR(20) | NOT NULL, DEFAULT 'ACTIVE', CHECK | 客户当前状态 |
| region | VARCHAR(50) | NULL | 客户所属地区（省级行政区名称） |
| open_date | DATE | NOT NULL | 客户开户日期 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**客户类型取值：**

- `INDIVIDUAL`：个人客户
- `BUSINESS`：企业客户

**客户状态取值：**

- `ACTIVE`：正常
- `INACTIVE`：非活跃
- `CLOSED`：已关闭

**地区取值（当前模拟数据）：**

`广东`、`北京`、`上海`、`浙江`、`江苏`、`四川`、`湖北`、`福建`

**业务规则：**

1. 每个客户使用唯一的 `customer_id` 标识。
2. 客户类型只能在预定义集合中选择。
3. 客户状态只能在预定义集合中选择。
4. 客户可以关联多个账户和多笔贷款。
5. 已有关联账户或贷款的客户不能直接删除。
6. `region` 由 `004_add_customer_region.sql` 新增，建表时可为空；数据库层未设置 `CHECK` 约束限制取值，地区合法性由数据生成器或数据质量检查保证。
7. `region` 可用于按地区对客户进行分组统计，例如各地区的客户数、账户数及交易量。

---

## 3. accounts（账户表）

**表名：** `source.accounts`

**业务说明：** 存储客户的银行账户信息，包括账户类型、账户状态和开户时间。

| 字段 | 数据类型 | 约束 | 业务含义 |
|---|---|---|---|
| account_id | BIGINT | PK, IDENTITY | 账户内部唯一标识 |
| customer_id | BIGINT | FK, NOT NULL | 所属客户 ID |
| account_type | VARCHAR(20) | NOT NULL, CHECK | 账户类型 |
| account_status | VARCHAR(20) | NOT NULL, DEFAULT 'ACTIVE', CHECK | 账户当前状态 |
| open_date | DATE | NOT NULL | 账户开户日期 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**账户类型取值：**

- `SAVINGS`：储蓄账户
- `CURRENT`：活期账户
- `CREDIT`：信用账户

**账户状态取值：**

- `ACTIVE`：正常
- `FROZEN`：冻结
- `CLOSED`：已销户

**业务规则：**

1. 一个客户可以拥有多个账户。
2. 每个账户必须关联已经存在的客户。
3. 账户类型和状态只能使用预定义取值。
4. 已有关联交易记录的账户不能直接删除。
5. 当前版本不直接存储账户余额，账户余额计算需要另行定义期初余额、交易方向及其他资金变动规则。

---

## 4. transactions（交易表）

**表名：** `source.transactions`

**业务说明：** 记录账户发生的存款、取款和转账交易，包括金额、交易状态和交易发生时间。

| 字段 | 数据类型 | 约束 | 业务含义 |
|---|---|---|---|
| transaction_id | BIGINT | PK, IDENTITY | 交易内部唯一标识 |
| account_id | BIGINT | FK, NOT NULL | 发生交易的账户 ID |
| transaction_type | VARCHAR(20) | NOT NULL, CHECK | 交易类型 |
| amount | NUMERIC(18,2) | NOT NULL, CHECK (amount > 0) | 交易金额 |
| transaction_status | VARCHAR(20) | NOT NULL, CHECK | 交易处理状态 |
| transaction_time | TIMESTAMPTZ | NOT NULL | 交易业务时间 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 记录更新时间 |

**交易类型取值：**

- `DEPOSIT`：存款
- `WITHDRAWAL`：取款
- `TRANSFER`：转账

**交易状态取值：**

- `PENDING`：处理中
- `SUCCESS`：成功
- `FAILED`：失败
- `CANCELLED`：已取消
- `REVERSED`：已冲正

**业务规则：**

1. 每笔交易必须拥有唯一的 `transaction_id`。
2. 每笔交易必须关联已经存在的账户。
3. 交易金额必须大于 0。
4. 交易类型和状态必须符合预定义取值。
5. 统计成功交易金额时，默认仅纳入 `transaction_status = 'SUCCESS'` 的交易，并按照报表口径处理冲正。
6. 已成功交易的撤销或冲正应保留可追溯记录，不直接抹除历史业务事实。
7. 当前模型只记录一个 `account_id`，尚不能完整描述转账双方账户及双边资金流水。
8. `transaction_time` 表示交易业务时间，`created_at` 表示数据库记录创建时间，两者不能混淆。
9. `updated_at` 由 `005_add_transactions_updated` 新增，表示记录最后一次更新时间，可用于增量抽取（`WHERE updated_at > 上次抽取时间`）或变更识别。
10. 当前 `updated_at` 仅在新增记录时取 `CURRENT_TIMESTAMP`，尚未配置 `ON UPDATE` 触发器或应用层回写；记录被修改时不会自动刷新，需要增量 ETL 或业务程序显式更新该字段。

---

## 5. loans（贷款合同表）

**表名：** `source.loans`

**业务说明：** 存储客户贷款合同信息，包括合同金额、贷款状态和合同日期。

贷款合同金额不一定等于已经实际发放的贷款金额，因此实际放款记录独立存储。

| 字段 | 数据类型 | 约束 | 业务含义 |
|---|---|---|---|
| loan_id | BIGINT | PK, IDENTITY | 贷款合同唯一标识 |
| customer_id | BIGINT | FK, NOT NULL | 借款客户 ID |
| contract_amount | NUMERIC(18,2) | NOT NULL, CHECK (contract_amount > 0) | 贷款合同约定金额 |
| loan_status | VARCHAR(20) | NOT NULL, CHECK | 贷款合同状态 |
| contract_date | DATE | NOT NULL | 贷款合同日期 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**贷款状态取值：**

- `PENDING`：待处理
- `ACTIVE`：正常进行中
- `PAID_OFF`：已结清
- `CANCELLED`：已取消

**业务规则：**

1. 一笔贷款必须关联已经存在的客户。
2. 贷款合同金额必须大于 0。
3. 一个客户可以拥有多笔贷款。
4. 一笔贷款可以对应多条实际放款记录。
5. 一笔贷款可以对应多条还款记录。
6. `contract_amount` 表示合同约定金额，不直接代表实际已放款本金。
7. 贷款剩余未偿本金需要结合成功放款和成功归还的本金计算。

---

## 6. loan_disbursements（实际放款表）

**表名：** `source.loan_disbursements`

**业务说明：** 记录贷款合同下实际发放的资金，支持一个贷款合同分多次放款。

| 字段 | 数据类型 | 约束 | 业务含义 |
|---|---|---|---|
| disbursement_id | BIGINT | PK, IDENTITY | 放款记录唯一标识 |
| loan_id | BIGINT | FK, NOT NULL | 所属贷款合同 ID |
| disbursement_amount | NUMERIC(18,2) | NOT NULL, CHECK (disbursement_amount > 0) | 本次放款金额 |
| disbursement_status | VARCHAR(20) | NOT NULL, CHECK | 放款处理状态 |
| disbursement_time | TIMESTAMPTZ | NOT NULL | 放款业务时间 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**放款状态取值：**

- `PENDING`：待处理
- `SUCCESS`：放款成功
- `FAILED`：放款失败
- `CANCELLED`：已取消

**数据库约束：**

- `disbursement_id` 为主键。
- `loan_id` 外键关联 `source.loans(loan_id)`。
- `(disbursement_id, loan_id)` 存在复合唯一约束。
- `loan_id` 和 `disbursement_time` 建有联合索引。

**业务规则：**

1. 每条放款记录必须关联有效贷款合同。
2. 每次放款金额必须大于 0。
3. 一笔贷款允许分多次实际放款。
4. 只有 `SUCCESS` 状态的放款计入实际已放款金额。
5. 业务上，正常贷款的累计有效放款不应超过合同约定金额。
6. 放款时间原则上不得早于贷款合同生效及相关审批要求允许的时间。
7. 当前 SQL 尚未实现跨记录的累计金额及时间先后校验，需要由业务程序或数据校验程序补充。

---

## 7. loan_repayments（贷款还款表）

**表名：** `source.loan_repayments`

**业务说明：** 记录贷款的实际还款情况，并将还款金额拆分为本金和利息，支持计算未偿本金及利息收入。

| 字段 | 数据类型 | 约束 | 业务含义 |
|---|---|---|---|
| repayment_id | BIGINT | PK, IDENTITY | 还款记录唯一标识 |
| loan_id | BIGINT | FK, NOT NULL | 所属贷款合同 ID |
| principal_amount | NUMERIC(18,2) | NOT NULL, DEFAULT 0, CHECK (>= 0) | 本次归还本金 |
| interest_amount | NUMERIC(18,2) | NOT NULL, DEFAULT 0, CHECK (>= 0) | 本次支付利息 |
| repayment_status | VARCHAR(20) | NOT NULL, CHECK | 还款处理状态 |
| repayment_time | TIMESTAMPTZ | NOT NULL | 还款业务时间 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |

**还款状态取值：**

- `PENDING`：待处理
- `SUCCESS`：还款成功
- `FAILED`：还款失败
- `CANCELLED`：已取消

**业务规则：**

1. 每条还款记录必须关联已经存在的贷款。
2. 本金与利息均不得为负数。
3. 本金与利息之和必须大于 0。
4. 还款总金额等于 `principal_amount + interest_amount`。
5. 只有 `SUCCESS` 状态的还款计入实际已还本金和已付利息。
6. 正常情况下，累计归还本金不得超过已实际发放且有效的本金。
7. 成功还款业务时间不得早于对应贷款的首次成功放款时间。
8. 当前版本将 `repayment_time` 定义为还款业务事件时间，不保证它一定代表最终成功入账时间。

---

## 8. 表之间的实体关系

| 主表 | 从表 | 关系 | 外键 |
|---|---|---|---|
| customers | accounts | 一对多 | accounts.customer_id |
| customers | loans | 一对多 | loans.customer_id |
| accounts | transactions | 一对多 | transactions.account_id |
| loans | loan_disbursements | 一对多 | loan_disbursements.loan_id |
| loans | loan_repayments | 一对多 | loan_repayments.loan_id |

**关系说明：**

- 一个客户可以拥有多个账户。
- 一个账户可以发生多笔交易。
- 一个客户可以拥有多份贷款合同。
- 一份贷款合同可以分多次放款。
- 一份贷款合同可以发生多次还款。

所有外键均要求关联记录存在，并使用 `ON DELETE RESTRICT` 阻止直接删除仍被引用的主表记录。

---

## 9. 统一数据规范

### 9.1 主键与外键

1. 所有主键采用 `BIGINT`。
2. 所有主键采用 PostgreSQL `GENERATED BY DEFAULT AS IDENTITY` 自动生成。
3. 外键必须关联已存在的主表记录。
4. 不允许生成孤立账户、孤立交易、孤立放款和孤立还款。

### 9.2 金额类型

1. 金额统一采用 `NUMERIC(18,2)`。
2. 不使用 `FLOAT` 存储精确货币金额。
3. 交易金额、合同金额及放款金额必须大于 0。
4. 还款本金和利息分别允许为 0，但两者之和必须大于 0。
5. 当前 V1.1 的 SQL 未设置币种字段，模拟数据统一按人民币（CNY）解释。

### 9.3 时间与日期

1. 时间戳统一采用 `TIMESTAMPTZ`。
2. 业务时区统一采用 `Asia/Shanghai`。
3. 日期字段采用 `DATE`。
4. `created_at` 表示数据库记录创建时间。
5. `updated_at` 表示数据库记录更新时间，当前仅 `source.transactions` 具备该字段。
6. `transaction_time`、`disbursement_time`、`repayment_time` 表示对应业务事件的时间。
7. 生成模拟数据时，应保证贷款合同、放款和还款之间的时间逻辑一致。
8. 当前 SQL 并未使用跨表约束强制实现时间先后规则。
9. 增量抽取依赖 `updated_at` 时，必须满足 `updated_at >= created_at`，且修改记录时同步刷新 `updated_at`。

### 9.4 业务状态

1. 状态字段采用 `VARCHAR(20)`。
2. 使用 `CHECK` 限制状态取值。
3. 状态初始值和合法转换应由业务逻辑管理。
4. `CHECK` 只能限制字段的取值集合，不能单独保证状态转换顺序。
5. 统计交易、放款和还款结果时，必须根据业务状态进行筛选。

### 9.5 数据完整性

1. 主键保证每条记录具有唯一标识。
2. 外键保证关联记录存在。
3. `NOT NULL` 限制必填字段。
4. `CHECK` 限制字段取值范围。
5. `UNIQUE` 限制唯一键组合。
6. 跨表累计金额、时间先后、状态转换等复杂业务规则应通过应用逻辑或独立的数据质量检查实现。

---

## 10. 常用业务统计口径

### 10.1 成功交易金额

统计条件：

`transaction_status = 'SUCCESS'`

计算口径：

`成功交易金额 = SUM(amount)`

按照账户、日期及交易类型分组统计。冲正、重复记账及转账双边计数问题需要按照具体业务口径处理。

### 10.2 实际累计放款

统计条件：

`disbursement_status = 'SUCCESS'`

计算口径：

`实际累计放款 = SUM(disbursement_amount)`

### 10.3 累计归还本金

统计条件：

`repayment_status = 'SUCCESS'`

计算口径：

`累计归还本金 = SUM(principal_amount)`

### 10.4 累计已付利息

统计条件：

`repayment_status = 'SUCCESS'`

计算口径：

`累计已付利息 = SUM(interest_amount)`

### 10.5 剩余未偿本金

计算口径：

`剩余未偿本金 = 累计成功放款本金 - 累计成功归还本金`

说明：该公式适用于当前简化模型的正常业务场景，尚未纳入本金冲正、核销、减免等复杂银行业务。

### 10.6 地区客户分布

分组字段：

`customers.region`

计算口径：

`各地区客户数 = COUNT(DISTINCT customer_id)`，可按 `region` 关联账户与成功交易，统计各地区账户数及成功交易金额。

说明：`region` 允许为空，统计时应单独列出 `region IS NULL` 的记录，避免漏计。需按客户维度计数时，应先对客户去重再关联账户和交易，防止多账户放大计数。

---

## 11. 数据生成器 V1 验收规则

后续 `data_generator/generate.py` 生成的数据至少应满足：

| 检查项目 | 验收要求 |
|---|---|
| 主键唯一性 | 所有记录的主键不得重复 |
| 外键完整性 | 外键必须引用存在的主表记录 |
| 客户状态 | 必须属于预定义状态集合 |
| 账户状态 | 必须属于预定义状态集合 |
| 金额合法性 | 金额满足相应 CHECK 约束 |
| 放款时间 | 成功放款不得早于合同允许放款时间 |
| 还款时间 | 成功还款不得早于对应贷款首次成功放款时间 |
| 放款总额 | 成功放款累计额不得超过合同金额 |
| 还款本金 | 成功归还本金累计额不得超过成功放款本金 |
| 贷款结清 | PAID_OFF 贷款应满足定义好的本金结清条件 |
| 状态统计 | 失败、待处理和取消记录不计入成功金额 |
| 数据可复现 | 固定随机种子后生成结果一致 |

---

## 12. 后续版本扩展字段

以下字段曾出现在初始设计中，但尚未在 `001_schema.sql` 实现，因此不属于当前 V1.2 数据库结构。

> 说明：`customers.region` 已通过 `004_add_customer_region.sql` 落地，`transactions.updated_at` 已通过 `005_add_transactions_updated` 落地，二者均已纳入正式字段，不再列入下表。

| 业务表 | 计划扩展字段 | 用途 |
|---|---|---|
| customers | customer_no | 客户业务编号 |
| customers | updated_at | 客户记录更新时间 |
| accounts | account_no | 账户业务编号 |
| accounts | balance | 账户当前余额 |
| accounts | currency | 账户币种 |
| accounts | closed_at | 账户销户时间 |
| transactions | currency | 交易币种 |
| transactions | business_date | 交易归属业务日期 |
| loans | interest_rate | 贷款约定利率 |
| loans | maturity_date | 贷款合同到期日 |
| loans | currency | 贷款币种 |
| loan_repayments | business_date | 还款归属业务日期 |
| loan_repayments | paid_at | 实际成功还款时间 |

后续扩展时，应同步更新建表 SQL、字段字典、模拟数据生成器和数据质量检查规则。

---

## 13. 版本记录

| 版本 | 主要变更 |
|---|---|
| V1.0 | 初始五张业务表的字段设计 |
| V1.1 | 统一实际 PostgreSQL 六张表结构；增加实际放款实体、状态约束、金额规则、索引及统计口径；明确后续扩展字段 |
| V1.2 | 新增 `customers.region`（客户所属地区，`004_add_customer_region.sql`）与 `transactions.updated_at`（记录更新时间，`005_add_transactions_updated`）；补充地区取值、增量抽取口径及时间规范 |

**文档维护原则：** 数据库结构、字段字典、数据生成器和测试脚本应保持一致。任何字段新增、删除、改名或业务口径调整，都需要同步更新相关文件。