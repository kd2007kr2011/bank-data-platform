# bank-data-platform
# Retail Banking Data Platform

零售银行数据平台：基于 PostgreSQL 与 Python 的业务数据处理与分析项目。

## 1. 项目简介

本项目面向零售银行的典型业务场景，模拟客户、账户、交易、贷款、放款及还款等业务数据，构建一个轻量级的数据处理与分析平台。

项目重点实践关系型数据库设计、SQL 数据查询与统计、Python 数据生成与处理、数据质量检查，以及业务指标建模等数据工程技术。

本项目定位为个人学习与工程实践项目，重点展示从业务需求分析到数据建模、数据处理和业务分析的完整开发流程。

**数据声明：本项目全部使用程序生成的合成数据，不包含真实银行业务数据或真实客户个人信息。项目仅用于学习、开发和演示，不代表任何真实银行的生产系统。**

## 2. 项目目标

- **业务建模：** 梳理零售银行客户、账户、交易、贷款及还款之间的业务关系。
- **数据管理：** 使用 PostgreSQL 建立业务数据表，并维护数据之间的关联。
- **数据处理：** 使用 Python 生成、整理和导入合成数据。
- **SQL 分析：** 实现多表关联、条件过滤、分组统计和常见业务指标计算。
- **数据质量：** 检查重复数据、缺失字段、无效关联及异常金额。
- **数据应用：** 为后续数据仓库分层、经营报表和可视化分析提供基础。

## 3. 业务范围

项目第一阶段覆盖以下业务对象：

| 业务对象 | 主要内容 |
|---|---|
| 客户 | 客户基本信息及客户状态 |
| 账户 | 账户信息及所属客户 |
| 交易 | 交易日期、交易类型、交易金额及交易状态 |
| 贷款 | 贷款合同及贷款状态 |
| 放款 | 实际放款记录及放款金额 |
| 还款 | 还款记录、还款金额及本金偿还情况 |

基于上述业务对象，逐步实现以下分析指标：

- 客户数与账户数
- 每日交易笔数及交易金额
- 不同交易类型的交易分布
- 贷款合同金额与实际放款金额
- 还款金额与贷款剩余本金

本项目暂不实现真实支付、真实贷款审批、生产级实时计算或复杂风险预测功能。

## 4. 技术路线

| 技术 | 主要用途 |
|---|---|
| PostgreSQL 18 | 业务数据存储、关系管理与 SQL 查询 |
| SQL | 多表关联、数据清洗、指标统计及数据质量检查 |
| Python 3.14 | 合成数据生成、数据导入及自动化处理 |
| Faker / NumPy / PyYAML | 合成客户信息、随机数生成与生成参数配置 |
| psycopg 3 | Python 与 PostgreSQL 的连接及 COPY 批量导入 |
| Git / GitHub | 版本控制、代码管理与项目展示 |
| Power BI 或其他可视化工具 | 后续业务报表与指标可视化，待后续阶段确定 |

### 开发流程

```text
业务需求分析
    ↓
数据模型设计
    ↓
生成合成业务数据
    ↓
PostgreSQL 建表与数据导入
    ↓
SQL 查询与数据质量检查
    ↓
业务指标统计
    ↓
数据仓库分层与可视化扩展
```

## 5. 项目目录结构

```text
bank-data-platform/
├── README.md
├── .env.example
├── requirements.txt
├── docs/
│   ├── requirements.md          # 需求说明
│   ├── data_dictionary.md       # 数据字典
│   ├── er_diagram.md            # ER 图
│   ├── layer_design.md          # 数据仓库分层设计
│   ├── daily_log.md             # 开发日志索引
│   ├── daily_log/               # 按开发日拆分的过程记录
│   └── check_and_accept/        # 阶段验收记录
├── sql/
│   ├── source/                  # 源层
│   │   ├── ddl/                 # 建表与 schema 创建
│   │   ├── seed/                # 手工种子数据
│   │   ├── alter/               # 字段与约束的增量变更
│   │   ├── trigger/             # 触发器
│   │   └── checks/              # 源层数据校验
│   ├── ods/
│   │   └── ddl/                 # ODS 建表（含交易最新状态表、拒收表）
│   ├── dwd/
│   │   ├── ddl/                 # DWD 建表与结构变更
│   │   ├── transform/           # DWD 加工 SQL
│   │   └── demo/                # 演示用表
│   ├── metadata/                # 元数据表（ETL 运行记录）
│   ├── analysis/                # 业务分析查询，按主题命名
│   └── checks/                  # 结构、约束与临时核对查询
├── etl/
│   ├── common/db.py             # 统一的数据库连接工厂
│   ├── extract/                 # 抽取：全量、增量
│   ├── load/                    # 装载：ODS 全量批次、ODS 增量
│   ├── dwd/                     # DWD 构建
│   ├── quality/                 # 数据质量规则
│   └── archive/                 # 被取代的历史版本，仅作留档
├── scripts/
│   ├── check_db.py              # 数据库连接与配置自检
│   ├── start_db.ps1             # 启动本地 PostgreSQL
│   ├── config/generator.yaml    # 生成参数（随机种子、日期范围、数据规模等）
│   └── generate/
│       ├── generate.py          # 生成六张表的合成 CSV
│       ├── validate.py          # 校验生成的 CSV 并输出报告
│       └── load_to_db.py        # 清空并批量导入 source 层数据
├── data/
│   ├── README.MD                # 数据说明
│   └── generated/               # 本地生成的 CSV，不提交仓库
│       ├── customers.csv
│       ├── accounts.csv
│       ├── transactions.csv
│       ├── loans.csv
│       ├── loan_disbursements.csv
│       ├── loan_repayments.csv
│       └── validation_report.txt
└── tests/
    ├── test_ods_rules.py        # ODS 质量规则单元测试
    ├── test_ods_integration.py  # ODS 增量装载集成测试
    └── test_idempotency.py      # 贷款快照幂等性与事务回滚测试
```

### 目录组织约定

1. **SQL 按数据层分目录**：`source` / `ods` / `dwd` / `metadata`；层内再按职责分子目录——`ddl` 建表、`transform` 加工查询、`alter` 结构变更、`checks` 校验查询。
2. **ETL 按处理阶段分目录**：`extract` 抽取 → `load` 装载 → `dwd` 明细构建；公共能力（连接、质量规则）放在 `common/` 与 `quality/`。
3. **文件名不写开发日编号**：脚本名 = 动作 + 对象（如 `build_loan_snapshot.py`）。同一职责只保留一个当前版本，被取代的版本移入 `etl/archive/`。
4. **测试统一在 `tests/`**：单元测试（不依赖数据库）与集成测试（依赖数据库）同目录，文件名以 `test_` 开头。
5. **代码与数据分离**：代码在 `etl/`、`scripts/`，生成数据在 `data/generated/`（已由 `.gitignore` 排除），文档在 `docs/`。

目录说明：

- `docs/`：项目需求、数据字典、ER 图、分层设计与开发过程记录。
- `sql/source/ddl/001_schema.sql`：源业务表结构、约束及索引定义。
- `sql/source/seed/002_seed.sql`：少量手工种子数据，用于快速验证约束。
- `sql/source/checks/003_validate.sql`：数据量、关联完整性及金额合法性检查。
- `sql/checks/constraint_failure_cases.sql`：外键、主键、CHECK 约束的失败用例测试。
- `sql/analysis/`：六类业务分析查询及执行计划、ETL 运行监控。
- `etl/extract/`、`etl/load/`、`etl/dwd/`：抽取、装载与明细构建脚本。
- `etl/quality/ods_rules.py`：ODS 数据质量规则与坏数据隔离逻辑。
- `scripts/generate/generate.py`：按配置生成六张表的合成 CSV。
- `scripts/generate/load_to_db.py`：清空并批量导入 `source` 层数据，同步自增序列。
- `scripts/generate/validate.py`：对生成的 CSV 做数据质量校验并输出报告。
- `scripts/check_db.py`：检查数据库连接及配置是否可用。
- `scripts/config/generator.yaml`：生成参数（随机种子、日期范围、数据规模等）。
- `data/generated/`：生成结果目录，属于本地数据，不纳入版本控制。
- `tests/`：单元测试与集成测试。

## 6. 数据来源与使用说明

### 数据来源

所有业务数据均由程序生成，用于模拟零售银行业务中的客户、账户、交易、贷款、放款和还款记录。

合成数据可根据项目需要设置客户数量、账户数量、交易日期、交易类型、交易状态、贷款金额及还款记录等字段。

### 数据使用原则

1. 不导入真实银行客户信息、账户流水或真实贷款记录。
2. 不在仓库中提交数据库密码、访问令牌或其他敏感凭据。
3. 合成数据中的金额、客户状态及业务事件仅用于功能演示，不代表真实银行业务分布。
4. 如后续引用公开数据集，将单独记录数据来源、许可条件及使用范围。

数据生成规则、字段含义和数据规模将在后续数据字典中进一步说明。

### 合成数据现状

数据由 `scripts/generate/generate.py` 按 `scripts/config/generator.yaml` 的参数生成，使用固定随机种子，结果可复现。

当前一批数据的生成参数：

| 参数 | 取值 |
|---|---|
| `seed` | 20261023 |
| `start_date` | 2022-01-01 |
| `end_date` | 2026-10-22 |
| `customers` | 1000 |
| `accounts_per_customer_min / max` | 1 / 3 |
| `transactions_per_account_min / max` | 3 / 12 |
| `loan_probability` | 0.30 |

生成结果（2026-10-23）：

| 表 | 行数 | 说明 |
|---|---:|---|
| `customers` | 1,000 | 个人客户 924，企业客户 76 |
| `accounts` | 2,057 | 平均每位客户约 2.06 个账户 |
| `transactions` | 15,467 | 成功 12,736，失败 1,008，待处理 793，已取消 587，冲正 343 |
| `loans` | 286 | 约 28.6% 的客户有贷款 |
| `loan_disbursements` | 286 | 每笔贷款一笔成功放款 |
| `loan_repayments` | 286 | 每笔贷款至少一笔还款，其中约 25% 已结清 |

- 业务日期覆盖 `2022-01-06` 至 `2026-10-22`。
- 数据规模约 1.6 MB，存放在 `data/generated/`，属于本地生成数据，不纳入版本控制。
- `scripts/generate/validate.py` 的校验结果为 `PASS`，错误数 `0`，报告见 `data/generated/validation_report.txt`。

当前校验覆盖：主键唯一、必填非空、外键关联有效、金额为正、账户开户日晚于客户开户日、交易不早于账户开户、放款不早于合同日期、还款不早于成功放款、放款总额不超过合同金额、已还本金不超过放款金额、`PAID_OFF` 贷款本金与放款金额一致，以及各状态字段的枚举合法性。

## 7. 环境要求

当前实际使用的环境：

- Python 3.14
- PostgreSQL 18（数据库名 `bank_dev`）
- Git
- Python 依赖见 `requirements.txt`：`psycopg[binary]`、`python-dotenv`、`Faker`、`numpy`、`PyYAML`

### 配置

1. 复制 `.env.example` 为 `.env`，填写数据库连接信息：

```text
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bank_dev
DB_USER=postgres
DB_PASSWORD=你的密码
```

2. 安装依赖：

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

`.env` 已被 `.gitignore` 排除，不会提交到仓库。

## 8. 项目运行

以下步骤均已在本地实际执行通过。

```bash
# 1. 启动 PostgreSQL（Windows PowerShell）
powershell -File scripts/start_db.ps1

# 2. 检查数据库连接和配置
.venv/Scripts/python scripts/check_db.py

# 3. 建表（只需执行一次；已存在时不会重建）
psql -U postgres -d bank_dev -f sql/source/ddl/001_schema.sql

# 4. 生成合成数据 CSV 到 data/generated/
.venv/Scripts/python scripts/generate/generate.py

# 5. 校验生成的 CSV
.venv/Scripts/python scripts/generate/validate.py

# 6. 清空 source 层并批量导入（单事务，失败自动回滚）
.venv/Scripts/python scripts/generate/load_to_db.py
```

### 8.1 分层建表

按顺序执行一次即可（均使用 `IF NOT EXISTS`，已存在时不会重建）：

```bash
psql -U postgres -d bank_dev -f sql/source/ddl/000_create_schemas.sql
psql -U postgres -d bank_dev -f sql/source/ddl/001_schema.sql
psql -U postgres -d bank_dev -f sql/ods/ddl/ddl.sql
psql -U postgres -d bank_dev -f sql/ods/ddl/transaction_current.sql
psql -U postgres -d bank_dev -f sql/ods/ddl/rejected_records.sql
psql -U postgres -d bank_dev -f sql/dwd/ddl/ddl.sql
psql -U postgres -d bank_dev -f sql/dwd/ddl/loan.sql
psql -U postgres -d bank_dev -f sql/metadata/etl_runs.sql
```

### 8.2 ETL 主链路

```bash
# Source -> ODS 增量装载（含质量检查与坏数据隔离）
.venv/Scripts/python etl/load/load_incremental.py

# ODS -> DWD 明细构建
.venv/Scripts/python etl/dwd/build_dwd_transactions.py
.venv/Scripts/python etl/dwd/build_dwd_loans.py

# 贷款快照（可重跑、可回补）
.venv/Scripts/python etl/dwd/build_loan_snapshot.py
```

### 8.3 测试

```bash
# 全部测试（tests.test_ods_rules 不依赖数据库，其余依赖）
.venv/Scripts/python -m unittest discover -s tests -t . -v

# 单独运行
.venv/Scripts/python -m unittest tests.test_ods_rules -v
.venv/Scripts/python -m unittest tests.test_ods_integration -v
.venv/Scripts/python -m unittest tests.test_idempotency -v
```

说明：

- `generate.py` 不连接数据库，只根据 `generator.yaml` 生成 CSV；修改 `seed` 可得到不同但可复现的数据。
- `load_to_db.py` 会先校验 `DB_NAME` 必须为 `bank_dev`，再 `TRUNCATE ... RESTART IDENTITY` 清空六张表，然后按外键顺序用 `COPY` 导入，最后同步自增序列。
- 数据质量检查 SQL 见 `sql/source/checks/003_validate.sql`；约束失败用例见 `sql/checks/constraint_failure_cases.sql`（该文件中的语句均预期报错，需逐条手动执行）。

## 9. 开发计划

- [x] 第一阶段：明确项目范围与初始需求。
- [x] 第二阶段：完成数据库设计与数据字典（六张源业务表、ER 图、数据字典 V1.1）。
- [x] 第三阶段：生成合成数据并完成数据库导入（1000 客户 / 15467 笔交易，校验通过）。
- [x] 第四阶段：实现基础 SQL 查询与数据质量检查。
- [x] 第五阶段：实现业务指标统计。
- [x] 第六阶段：扩展数据仓库分层（Source / ODS / DWD / Metadata）与增量装载、幂等重跑。
- [ ] 第七阶段：完善测试、运行文档及项目展示。

## 10. 项目定位

本项目用于学习和实践零售银行数据工程的基本流程，逐步建立从业务需求到数据模型、数据处理、指标分析及数据应用的工程能力。

项目将持续完善代码、文档和测试，并以可复现的运行流程作为主要验收依据。
