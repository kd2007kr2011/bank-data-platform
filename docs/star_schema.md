
# D15 银行数仓维度建模设计

## 1. 建模目标

基于前期完成的 ODS 数据清洗和 DWD 业务明细，
构建面向银行业务分析的维度模型。

本阶段采用星型模型设计思想，实现：

- 客户维度
- 地区维度
- 日期维度
- 交易事实
- 贷款每日快照事实

为后续 DWS 指标汇总和 ADS 分析提供基础。

## 2. 事实表粒度

### fact_transaction

粒度：一笔交易。

唯一业务键：transaction_id。

主要指标：

- amount：交易金额

关联维度：

- customer_key
- region_key
- date_key

### fact_loan_daily

粒度：一笔贷款在一个日期的状态。

唯一业务键：

(loan_id, date_key)

主要指标：

- total_disbursed
- total_repaid_principal
- outstanding_principal
- overdue_days

关联维度：

- customer_key
- region_key
- date_key

其中 outstanding_principal 是存量指标，
只能在相同日期、不同贷款间直接汇总。

## 3. 维度表设计

### dim_customer

客户维度。

业务主键：customer_id。

代理主键：customer_key。

当前采用 SCD Type 1。

客户属性变化时覆盖旧值。

### dim_region

地区维度。

代理主键：region_key。

业务唯一键：region_name。

### dim_date

日期维度。

主键：date_key。

格式：YYYYMMDD。

包括年、季度、月、日、周等日期属性。

注意：
当前 is_weekend 仅识别周六、周日，
不代表中国法定节假日或银行营业日。

## 4. 代理键设计

维度表使用数据仓库内部的代理键，
避免过度依赖业务系统主键。

事实表通过代理键关联维度表。

## 5. 退化维度

交易流水号 transaction_id
直接保留在交易事实表中。

贷款编号 loan_id
直接保留在贷款日快照事实表中。

不为这些编号单独创建维度表。

## 6. SCD 设计

当前实现：

SCD Type 1。

客户地区变更时更新当前维度记录。

后续可以升级：

SCD Type 2。

使用有效开始时间、结束时间和版本标识
保存客户历史属性。

## 7. 星型模型关联

两张事实表分别与三个共享维度关联。

维度键关系：

dim_customer.customer_key
    -> fact_transaction.customer_key
    -> fact_loan_daily.customer_key

dim_region.region_key
    -> fact_transaction.region_key
    -> fact_loan_daily.region_key

dim_date.date_key
    -> fact_transaction.date_key
    -> fact_loan_daily.date_key

以上表示共享维度关联，
不是事实表之间相互连接。

## 8. 数据质量要求

1. 客户业务键不能重复。
2. 地区名称不能重复。
3. 交易流水号不能重复。
4. 贷款编号 + 日期不能重复。
5. 事实表的维度外键必须有效。
6. 金额字段应满足业务约束。
7. ETL 重跑不得产生重复事实记录。
8. 维度 JOIN 不应造成事实记录被重复统计。

## 9. 设计限制

当前客户维度采用 SCD Type 1。

历史事实中的地区关联可能随着客户当前
地区变化而改变。

如果要求严格复现交易发生时的客户地区，
应当保留历史地区属性或升级 SCD Type 2。

贷款指标复用前期 D13 的计算结果，
不在本阶段重复聚合放款和还款事件。

## 10. D15 验收标准

- 完成五张模型表的 DDL。
- 维度表数据成功装载。
- 事实表支持按唯一业务键 UPSERT。
- 星型模型查询可以正常执行。
- 交易和贷款统计不存在重复计数。
- 完成建模文档并提交 Git。
