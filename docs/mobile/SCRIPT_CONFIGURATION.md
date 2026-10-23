# 手机执行脚本接入

本分支按已确认的迁移方案实现集中定位与现有物理设备执行链，保留原module1任务/进度接口。
mobile_locators.py、mobile_adapter.py、mobile_executor.py已完成离线验证，尚未在B接入执行。
系统双开名册、指定空间启动、前台实例核对及网页数量适配仍待后续实施；当前执行入口明确拒绝带android_user_id的实例，避免按默认主程序误执行。

## 真实接口依据

B报告确认Python 3.7.4，手机对象为xbot.mobile.appium.session.MobileSession。
XPath查询、元素点击/输入、截图、光标输入、后退、滑动、UI树及屏幕尺寸方法签名已经取得。
lxml可用。现有OCR扩展activity_179ea575的__init__.py公开process1入口及中文参数已取得，可以直接从Python调用，当前无需保留OCR卡片桥接。
两份报告仍未包含当前手机可视化流程正文；不再据此要求新一轮采集，业务以已确认F01—F61和定位正文为依据。
报告中工程/OCR源码只作私有核对，不提交公共仓库。

## 模块

| 文件 | 职责 |
| --- | --- |
| mobile_locators.py | 27项定位编号、静态/参数化XPath、全局同名候选封面及结果卡片路径、OCR文字 |
| mobile_adapter.py | 按真实签名调用手机与OCR；同一份XML复用候选/卡片签名；加载检查入口check_environment |
| mobile_executor.py | 搜索、筛选、作者核验、原两种评论分支、互动、返回、即时记录及异常出口；入口run(phone_device, device_identity) |

除上述新增模块外，当前module1.py、core_runner.py和原流程未由本阶段修改。
安装到B时在现有应用新建三个同名Python模块，分别整体粘贴完整源码并保存。模块名不填.py后缀。

## 当前先做加载检查

沿用主流程已插入的第7行调用，将其改为以下配置：

| 项目 | 值 |
| --- | --- |
| 模块 | mobile_adapter |
| 函数 | check_environment |
| phone_device | Python表达式：phone_devices[0] |
| 返回类型 | 字典 |
| 输出变量 | mobile_environment_result |

保留第8行start_execution断点，从第1行运行。暂停在第8行时停止本次运行。
日志应输出“手机执行模块环境检查通过：Python 3.7.4，离线OCR入口可用。”
该函数检查三个模块能否加载及实际手机/OCR入口是否存在，不执行手机动作或OCR识别。
本步骤不要求再次输出接口JSON，不先删除或禁用原子流程/原Py文件。

## 加载通过后的接入依据

子流程1入口及phone_device、device_identity参数保持。接入执行入口时，先整体禁用原操作块，保留原内容，再新增一个调用；不重新搭建198行。实际行号以B当时界面为准，不根据旧198行表伪造最终逐行配置。

| 项目 | 值 |
| --- | --- |
| 模块 | mobile_executor |
| 函数 | run |
| phone_device | Python表达式：phone_device |
| device_identity | Python表达式：device_identity |
| 返回类型 | 字典 |
| 输出变量 | mobile_execution_result |

执行入口读取原绑定任务，承接已分配评论、令牌、计划和成功记录。每个动作正常返回后立即调用原record_action_result。
异常保留原文并用原finish_device_error结束当前绑定任务；该出口未能结束时继续抛出原异常，由现有主流程Catch处理。
已成功动作不重做，不重新随机计划。NOT_FOUND仍走原finish_task与原核心校验。

## 已完成的检查与边界

- 37项离线检查通过，包含原定位、旧AST兼容、原生/OCR适配、视频/图文分支、即时保存、续执行、候选核验回退、每方向6次栏目滑动及结果扫描停止。
- 三个运行模块通过Python 3.7语法检查；实际测试运行环境为Python 3.12，不冒充B的Python 3.7真机执行。
- 30份已提供UI树中有12份结果树，均能生成节点卡片签名；移除ID后签名一致。此前46组作者—封面关系及两份好友树定位已离线核对。
- B当前只运行过接口采集；新模块加载、搜索/OCR/互动链及双开均未由本阶段冒充实机通过。

