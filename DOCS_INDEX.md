# 文档索引

## 当前入口

| 文件 | 用途 |
| --- | --- |
| [脚本迁移方案](MOBILE_SCRIPT_MIGRATION_PLAN.md) | 已批准的脚本优先实施、五项调整、模块边界与双开接入 |
| [新会话实施入口](MOBILE_IMPLEMENTATION_HANDOFF.md) | 直接开始配置，不重搭198行 |
| [完整执行流程](docs/mobile/EXECUTION_FLOW.md) | F01—F61逐步流程与评论/回退分支；对应flow_plan.json |
| [全部定位规则](docs/mobile/ELEMENT_LOCATORS.md) | 27项规则与L13动态表达式；对应locator_plan.json |
| [手机执行需求](MOBILE_EXECUTION_REQUIREMENTS.md) | 已确认的集中定位、子流程压缩、双开自动识别与独立执行需求；区分确认目标和未实现事项 |
| [设备统一执行记录](DEVICE_STANDARDIZATION_20261022.md) | 2026-10-22三大设备任务、APK提取/分发、保留数据回退命令、回退验证进度及后续设备复用 |
| [README.md](README.md) | 完成状态与日常启动入口 |
| [PROJECT_RULES.md](PROJECT_RULES.md) | 当前工作规则与禁止偏离项 |
| [NEW_SESSION_START.md](NEW_SESSION_START.md) | 新会话接续状态 |
| [REUSE_GUIDE.md](REUSE_GUIDE.md) | 复用、安装、参数和已知等待说明 |
| [CURRENT_FLOW.md](CURRENT_FLOW.md) | 20/198行关键接口台账 |
| [MILESTONE_20261014.md](MILESTONE_20261014.md) | 完成节点、事实依据、最终导出缺口 |
| [VERSION_BASELINE.md](VERSION_BASELINE.md) | 原安装包、版本与校验值 |
| [templates/settings.json](templates/settings.json) | 冷却配置示例 |
| [packages/README.md](packages/README.md) | 包用途与安装顺序 |

## 运行源码

core_runner.py负责任务、分配、动作进度及冷却；module1.py是影刀桥接；lan_bridge.py和lan_tool负责一个网页工具；install_tool.py、setup_tool.ps1、Start-Tool.cmd负责原安装/启动。源码路径保持，不因整理调整手机动作。

现有tests与validation保留。不要把历史测试文件、静态检查或接口返回冒充新的B真机运行结果。

## 历史资料

[docs/history/INDEX.md](docs/history/INDEX.md)保留2026-10-06至10-12规划、实施、迁移与故障原文。旧README和重复长接续记录不再作为当前部署入口。旧flow-plan.json及CURRENT_FLOW.png属于历史流程快照，不代表20/198行配置。

ui_sources/保留原始UI树证据，作为真实定位变更时的同用途对照。docs/history/tools/中的设备采集脚本和module1.baseline.py只作历史资料，不是当前启动前置条件。
