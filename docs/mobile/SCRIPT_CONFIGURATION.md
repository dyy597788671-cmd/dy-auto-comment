# 脚本配置：集中定位与真实接口采集

本分支承接已确认的MOBILE_SCRIPT_MIGRATION_PLAN.md，不改变F01—F61业务。
本阶段完成集中定位及接口采集工具，尚未交付mobile_executor、mobile_adapter或双开实现。

## 已完成

- mobile_locators.py：集中管理27项编号，包含21项固定/参数化XPath、L13全局同名候选表达式、L18同卡片路径及3项OCR文字。
- L01通过实例身份处理；L18的完整签名提取与计数属于后续执行模块，本阶段仅提供同卡片定位。
- 运行模块只使用Python标准库；开发测试用lxml验证XPath 1.0。
- 30份现有UI树中有12份结果树，46组作者—封面关系各命中1个；去除全部ID后仍一致。2份分享树命中好友规则。
- 8项回归通过，覆盖传统/Compose混合顺序、全局同名序号、两种引号、模板变量样式的昵称、输入焦点及好友关系。
- 接口采集使用模拟对象验证，未触发手机属性读取或手机动作。以上均为离线检查，尚未在B部署运行。

## 当前先配置一个接口采集调用

1. 在现有影刀应用中新建Python模块mobile_interface_probe，将同名文件完整源码粘贴进去并保存。
2. 在主流程现有连接汇总完成之后、start_execution调用之前插入“调用模块”。依据CURRENT_FLOW.md，该位置是原第6行与原第7行之间。

| 项目 | 值 |
| --- | --- |
| 模块 | mobile_interface_probe |
| 函数 | collect |
| phone_device | Python表达式：phone_devices[0] |
| 返回类型 | 字符串 |
| 输出变量 | interface_report_path |

3. 在原start_execution调用那一行设置断点，从第1行运行。到该断点暂停时，前一条采集调用已完成。
4. 在文件资源管理器地址栏输入%TEMP%，取出dy_mobile_interface.json，供下一步接口适配读取。

报告包含当前手机对象的类名、方法签名/说明及本应用生成的手机/OCR调用代码。
只读取当前应用顶层Python调用代码及已加载手机模块，不读取任务表、运行状态或数据库。
报告只用于本次接口适配，不提交公共仓库。

## 后续

按报告中的当前真实方法完成mobile_adapter和mobile_executor，复用原module1进度接口。
随后接入子流程及双开身份、启动和数量链。集中定位模块届时与执行模块一起接入。
