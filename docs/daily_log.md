完成五张源业务表的 DDL 文件。
为表结构添加主键、外键、唯一约束及 CHECK 约束。
编写独立的异常测试 SQL。
学习基础 SQL 建表、数据插入和约束语法。
记录非法数据测试的预期结果与实际结果。

---

## 2026-10-23

**数据生成与导入**

- 新增 `scripts/config/generator.yaml`，把随机种子、日期范围、客户数、账户数、交易数及贷款概率做成可配置参数。
- 编写 `scripts/generate/generate.py`，按配置生成六张表的合成 CSV，固定随机种子，结果可复现。
- 编写 `scripts/generate/validate.py`，对生成的 CSV 做数据质量校验，输出 `validation_report.txt`。
- 编写 `scripts/generate/load_to_db.py`，用 `COPY` 批量导入并按外键顺序加载，最后同步自增序列。

**生成结果**

| 表 | 行数 |
|---|---:|
| customers | 1,000 |
| accounts | 2,057 |
| transactions | 15,467 |
| loans | 286 |
| loan_disbursements | 286 |
| loan_repayments | 286 |

业务日期覆盖 2022-01-01 到 2026-10-22，校验结果为 PASS，错误数 0。

**修复的问题**

- `.env` 路径解析错误：脚本从 `scripts/` 找配置文件，实际在项目根目录，导致 `KeyError: 'DB_PASSWORD'`。
- 误删库保护不足：改为连接前校验 `DB_NAME`，连接后再用 `current_database()` 复核。
- 缺文件、空表、`pg_get_serial_sequence` 返回 NULL 时缺少明确提示或回退处理。
- `README.md` 为 UTF-16LE 编码，统一转为 UTF-8。
- `sql/other_sql.sql` 中第一条插入语句引用了不存在的列 `repayment_amount`。
- 文档中的建表文件路径由 `sql/source/001_schema.sql` 更正为 `sql/001_schema.sql`。

**待办**

- `docs/requirements.md` 仍写的是 MySQL，待与实际 PostgreSQL 实现统一。
- 第四阶段：基础 SQL 查询与指标统计。


