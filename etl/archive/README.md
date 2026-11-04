# 历史归档

本目录保存项目开发过程中被后续版本取代的脚本，仅作过程留档与对照使用，
**不参与日常运行**。日常请使用 `etl/` 下对应目录中的当前版本。

| 归档文件 | 被取代于 | 当前版本 | 差异 |
|---|---|---|---|
| `load_incremental_d10.py` | — | `etl/load/load_incremental.py` | 归档版只做增量装载；当前版增加了 ODS 数据质量检查、坏数据写入 `ods.rejected_records`，并把目标写入与运行状态放进同一事务 |
| `build_loan_snapshot_v1.py` | — | `etl/dwd/build_loan_snapshot.py` | 归档版一次性执行 `sql/dwd/transform/loan_snapshot.sql`；当前版支持按业务日幂等重跑、历史回补与重跑审计日志 |

两份归档文件均已同步为当前的导入与路径写法，可直接阅读；如需执行，
请先确认它们不会与当前版本写同一张表。
