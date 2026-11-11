# 数仓表文档索引

本项目的表结构文档按数据层拆分：

| 数据层 | 文档 | 内容 |
|---|---|---|
| Source | [source_table_dictionary.md](source_table_dictionary.md) | Source 表清单、最终字段、约束、索引和表关系 |
| ODS | [ods_table_dictionary.md](ods_table_dictionary.md) | ODS 表清单、字段、约束和血缘 |
| DWD | [dwd_table_dictionary.md](dwd_table_dictionary.md) | DWD 明细、快照、维度、事实表字段字典 |

已有的 [data_dictionary.md](data_dictionary.md) 保留为更详细的 Source 业务规则说明；`source_table_dictionary.md` 用于和 ODS、DWD 文档保持统一结构。

## 维护规则

1. 新增或修改 DDL 时，同步修改对应层的表结构字典。
2. 字段类型、可空性、默认值和状态集合以 SQL DDL 为准。
3. 同名表存在多份 DDL 时，应在文档中写明执行顺序和最终结构。
4. 演示表、临时表与正式表分开记录，不混入正式表清单。
