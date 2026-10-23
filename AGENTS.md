# 项目执行入口

2026-10-23当前确认：用户替换OCR修正文件后反馈“可运行”，要求同步GitHub；后续出现实际问题再处理，本阶段收口，不新增配置或继续全面测试。前端实例数量识别正确，常驻运行时新任务已自动领取执行。三账号筛选失败的共同原因为OCR公开入口返回list，mobile_adapter却读取对象属性OCR识别结果；现已兼容直接列表、单层输出包装及原字典/对象形式，并补充筛选两按钮的回归检查。当前结果是用户实测可运行，不扩写为所有设备、作品类型与续执行场景逐项通过。

当前代码、安装包和复用步骤见[脚本接入](docs/mobile/SCRIPT_CONFIGURATION.md)及[多开接入](docs/mobile/MULTI_INSTANCE_CONFIGURATION.md)。以下“待部署”“待接入”均为历史阶段，不覆盖本次用户确认，也不要求重复采集接口或重配流程。

2026-10-23最新：用户要求立即接入多开，实例代码和更新入口已编写，尚未部署到B。优先读[多开接入](docs/mobile/MULTI_INSTANCE_CONFIGURATION.md)。mobile_instances负责实际用户空间枚举、启动及前台核对；module1展开实例名单；core允许共享物理手机但保持活动互斥与独立进度；网页读取实例名册计数。原主身份不变，旧任务不重新分配。更新包使用Apply-Instances.cmd，后续Start-Tool.cmd仅启动已安装后台，不能再调用旧v1.1.0安装器覆盖代码。本节优先于下方较早的“尚未实施双开”状态。

2026-10-23当前任务：按已确认方案接入集中定位与手机执行脚本。先完整读[脚本接入当前状态](docs/mobile/SCRIPT_CONFIGURATION.md)、[实施交接](MOBILE_IMPLEMENTATION_HANDOFF.md)、[迁移方案](MOBILE_SCRIPT_MIGRATION_PLAN.md)及两份流程/定位正文。mobile_locators、mobile_adapter、mobile_executor已形成并通过37项离线检查，尚未在B接入执行；当前先在B新建三个Python模块并调用mobile_adapter.check_environment。两份B报告已确认Python3.7.4、手机/元素接口、lxml可用性及OCR公开process1入口，不再要求重采这些接口。现有物理设备执行链已编码，双开名册、定向启动及网页数量链仍待适配，不得写成双开已实现。保留原主流程、子流程入口、module1与业务数据，不重搭198行。

版本统一、小米登录及回退可行性已经确认，复用[设备统一执行记录](DEVICE_STANDARDIZATION_20261022.md)；双开自动枚举、分别启动与独立进度要求见[手机执行需求](MOBILE_EXECUTION_REQUIREMENTS.md)。不重做已通过安装，不把归档缺口变成全面重搭流程的理由。


先完整读取[PROJECT_RULES.md](PROJECT_RULES.md)，再读取[NEW_SESSION_START.md](NEW_SESSION_START.md)、[MILESTONE_20261014.md](MILESTONE_20261014.md)及当前操作对应的完整依据。

当前为2026-10-14顺序执行完成节点。复用先读[REUSE_GUIDE.md](REUSE_GUIDE.md)，不按docs/history的旧待办重新开发或重复核查已经通过的手机流程。

用户指令优先。没有真实界面或同用途完整证据不猜字段、行号、属性或结果；有真实缺口只取最少材料。多设备同时执行尚未实施，只在用户以后明确要求时进入该阶段。

