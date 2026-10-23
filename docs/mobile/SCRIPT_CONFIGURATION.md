# 手机执行脚本接入

最新进度（2026-10-23）：三个手机模块及实例接入已部署。用户确认前端数量识别正确，常驻运行可自动领取网页新任务；替换OCR修正模块后反馈“当前测试结果：可运行”。用户要求后续出现实际问题再处理，本阶段不继续扩展配置或全面重测。安装与复用见[MULTI_INSTANCE_CONFIGURATION.md](MULTI_INSTANCE_CONFIGURATION.md)。

本分支按已确认方案实现集中定位、手机执行及主副实例名单、定向启动、独立状态和网页计数，沿用module1任务/进度接口。

## 本次OCR错误与修正

现场三个执行账号均在搜索筛选弹窗后失败，保存错误为`'list' object has no attribute 'OCR识别结果'`。OCR已被调用，失败发生在返回值解析，尚未匹配或点击“一天内”。原代码只兼容字典和带属性对象，现场公开入口却返回list，因此读取output.OCR识别结果时报错；原异常出口将当前账号记失败并继续下一账号。

mobile_adapter.ocr_screen现兼容直接结果列表、单层输出列表包装及原字典/对象形式；空列表保留为空，不改OCR阈值、定位文字或执行顺序。回归覆盖实际list形式和“一天内→查看结果→结果扫描”；适配与执行相关24项离线检查通过，Python3.7语法通过。用户已替换该完整模块并确认可运行。

当前B无需再次替换或重配调用卡片。packages/Douyin-Instances-Update.zip尚未包含同一修正；以后复用旧包后，须在影刀编辑器中完整替换mobile_adapter.py为仓库当前源码并保存。以下加载和接入步骤保留为首次配置参考，不是当前待办。

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

本次OCR修正只修改mobile_adapter.py及对应回归检查；不改变任务分配、互动逻辑或原流程。前一阶段实例接入的module1/core改动见多开说明。
安装到B时在现有应用新建三个同名Python模块，分别整体粘贴完整源码并保存。模块名不填.py后缀。

## 首次配置：加载检查（当前B已完成）

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
- B已加载、接入并实际运行当前模块，用户确认修正后可运行；未将这一反馈扩写为所有设备、作品类型及续执行场景逐项通过。上方旧离线检查数量为当时记录，本次修正以24项相关检查和用户实测反馈为准。

