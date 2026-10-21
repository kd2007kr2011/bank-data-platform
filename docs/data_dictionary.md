
# 银行业务字段字典

## 1. customer（客户表）

| 字段 | 数据类型 | 约束 | 业务含义 |
|---|---|---|---|
| customer_id | BIGINT | PK, NOT NULL | 客户内部唯一标识 |
| customer_no | VARCHAR(32) | UNIQUE, NOT NULL | 客户业务编号 |
| full_name | VARCHAR(100) | NOT NULL | 客户姓名 |
| created_at | TIMESTAMPTZ | NOT NULL | 记录创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | 最近更新时间 |

## 2. account（账户表）

| 字段 | 数据类型 | 约束 | 业务含义 |
|---|---|---|---|
| account_id | BIGINT | PK, NOT NULL | 账户内部唯一标识 |
| customer_id | BIGINT | FK, NOT NULL | 所属客户 ID |
| account_no | VARCHAR(32) | UNIQUE, NOT NULL | 账户业务编号 |
| balance | NUMERIC(18,2) | NOT NULL | 账户余额 |
| currency | CHAR(3) | NOT NULL | ISO 4217 货币代码 |
| status | VARCHAR(20) | NOT NULL | 账户状态 |
| opened_at | TIMESTAMPTZ | NOT NULL | 开户时间 |
| closed_at | TIMESTAMPTZ | NULL | 销户时间 |

## 3. bank_transaction（交易表）

| 字段 | 数据类型 | 约束 | 业务含义 |
|---|---|---|---|
| transaction_id | BIGINT | PK, NOT NULL | 交易内部唯一标识 |
| account_id | BIGINT | FK, NOT NULL | 发生交易的账户 ID |
| transaction_type | VARCHAR(20) | NOT NULL | 交易类型 |
| amount | NUMERIC(18,2) | NOT NULL | 交易金额 |
| currency | CHAR(3) | NOT NULL | 交易币种 |
| occurred_at | TIMESTAMPTZ | NOT NULL | 实际发生时间 |
| business_date | DATE | NOT NULL | 归属业务日期 |
| status | VARCHAR(20) | NOT NULL | 交易状态 |

## 4. loan（贷款表）

| 字段 | 数据类型 | 约束 | 业务含义 |
|---|---|---|---|
| loan_id | BIGINT | PK, NOT NULL | 贷款内部唯一标识 |
| customer_id | BIGINT | FK, NOT NULL | 借款客户 ID |
| principal_amount | NUMERIC(18,2) | NOT NULL | 贷款本金 |
| currency | CHAR(3) | NOT NULL | 贷款币种 |
| interest_rate | NUMERIC(8,6) | NOT NULL | 约定利率 |
| status | VARCHAR(20) | NOT NULL | 贷款状态 |
| maturity_date | DATE | NOT NULL | 约定到期日 |

## 5. repayment（还款表）

| 字段 | 数据类型 | 约束 | 业务含义 |
|---|---|---|---|
| repayment_id | BIGINT | PK, NOT NULL | 还款内部唯一标识 |
| loan_id | BIGINT | FK, NOT NULL | 对应贷款 ID |
| amount | NUMERIC(18,2) | NOT NULL | 本次还款金额 |
| currency | CHAR(3) | NOT NULL | 还款币种 |
| paid_at | TIMESTAMPTZ | NULL | 实际还款时间 |
| business_date | DATE | NOT NULL | 归属业务日期 |
| status | VARCHAR(20) | NOT NULL | 还款状态 |

## 6. 统一规则

- 时间戳统一采用 TIMESTAMPTZ。
- 业务时区统一采用 Asia/Shanghai。
- 金额采用 NUMERIC，不使用 FLOAT 存储精确货币金额。
- 货币代码采用 ISO 4217 标准。
- 主键保证记录唯一，外键保证关联记录存在。
- 状态字段采用约定的有限值集合。


## 交易业务规则

1. 每条交易记录使用唯一的 `transaction_id` 标识。
2. `amount` 必须大于 0，交易方向由 `transaction_type` 区分。
3. `status` 用于记录交易处理结果，初始状态及允许的状态转换应在业务设计中明确。
4. 成功交易金额统计仅包含符合统计口径的成功交易。
5. 已成功交易的撤销或冲正应保留相应的业务记录，不直接覆盖历史事实。

## 还款业务规则

1. 每条还款记录通过 `loan_id` 关联对应贷款。
2. `amount` 必须大于 0。
3. 只有成功完成的还款才计入已还金额，处理中或失败的还款不计入。
4. `paid_at` 表示实际完成还款的时间；未完成的还款不应填写虚假的完成时间。
5. 贷款剩余应还金额应依据贷款本金、利息、费用及已确认的还款记录，按照约定的计算规则确定。