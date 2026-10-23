# 多开接入与安装

本分支已编写实例枚举、按空间启动、前台实例核对、共享连接顺序执行、独立进度和网页数量适配。B尚未安装本次更新，主副启动及影刀操作副本仍待B真机验证；离线通过不代表已在手机通过。

## 安装

1. 保存影刀当前应用，停止流程并完全退出影刀；关闭原网页后台窗口。
2. 将Douyin-Instances-Update.zip的全部文件直接解压到原工具启动目录，与原setup_tool.ps1同级。使用原目录，覆盖同名工具文件；不另建内层目录。
3. 双击Apply-Instances.cmd。脚本只读取原setup_tool.ps1里的应用目录、Runtime和端口常量，不执行旧安装器。使用此前已验证的Python313，安装实例代码，并调用现有原生签名脚本。
4. 更新结果应出现VERSION=1.2.0、RESULT=INSTANCES_UPDATED（重复执行为ALREADY_CURRENT）、签名检查通过及本机HTTP检查通过。保持后台窗口开启。
5. 重开影刀，从主流程第1行运行，刷新网页查看连接手机数、可用抖音数和调用数量。主流程现有start_execution、prepare_devices及子流程run的参数无需改动。

以后仍使用Start-Tool.cmd启动网页。更新包中的这个入口改为仅启动已安装后台，不再调用旧setup_tool.ps1覆盖执行代码。原setup_tool.ps1保留为路径配置来源，不再是日常启动入口。

当前子流程接入应为mobile_executor.run(phone_device, device_identity)，原操作块禁用；其完整字段见SCRIPT_CONFIGURATION.md。这里不重搭原流程。

## 数量与身份

- 主流程按真实用户空间枚举已启用且有启动入口的抖音。用户空间从手机读取，不把双开编号写死。
- 四台手机实际有七个可启动抖音，网页显示连接手机4台、可用抖音7个，任务可选7。不开双开的手机只贡献实际的一个实例。
- 物理手机标识、Android用户空间和包名共同标识实例。同手机实例使用同一个connection_index和phone_device，依次执行。
- 原主程序继续使用原设备_UDID执行身份，保留旧任务分配、评论、计划、成功动作、冷却和续发；新增副本获得独立身份。
- 主、副按用户空间分别启动，读取前台ActivityRecord确认空间和包名后才进入原操作流程；不以相同包名代替实例确认。
- 每个实例独立保存冷却、评论和动作；同手机已有活动任务时，原物理互斥检查仍阻止另一个实例同时领取。
- 旧任务继续按原分配执行，不因新增副本重新分配；新任务按新的实例名单分配。

## 网页读取

影刀在start_execution及prepare_devices中读取实例，原子写入data/mobile_instances.json。网页只读取该名单，与已登记且实时在线的手机取交集；网页请求不执行手机shell命令，不启动ADB或建立Appium会话。

首次安装需从主流程第1行运行一次产生名册。没有名册时网页明确提示读取实例，不用手机数量乘二，也不把物理数量冒充抖音数量。枚举失败不沿用该手机上次的可执行名单，原因保留在名册和网页提示中。

安装器保留data、config、logs、SQLite、UUID及可视化流程。module1只替换_device_bindings和prepare_devices；其它业务函数及原路径前缀保留。新增mobile_instances放在应用根，手机操作仍由原影刀连接执行。

## 验证边界

针对实例、安装、HTTP接口及原手机脚本的60项离线检查通过；覆盖四台七实例、非固定双开编号、主副共享物理连接、独立冷却/续发、物理互斥、旧身份保留、前台空间错误阻止执行、网页计数及提交校验、安装幂等和业务数据保留。7份运行模块通过Python3.7语法检查，JavaScript语法检查通过。

已在隔离目录读取用户提供的当前状态文件，5个项目和4个设备记录可按新结构加载，文件保持原字节；用户状态不随包交付或提交仓库。

离线执行环境为Python3.12。Windows PowerShell安装链和真实Android主副切换尚未在B执行。仓库较早的非mobile测试存在与现行核心/安装接口不匹配的历史断言，不能用本次定向检查冒充整个历史测试集通过。

Android接口依据：[ADB服务协议](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/dev/services.md)、[用户信息标志](https://android.googlesource.com/platform/frameworks/base/+/master/core/java/android/content/pm/UserInfo.java)、[按用户解析应用入口](https://android.googlesource.com/platform/frameworks/base/+/main/services/core/java/com/android/server/pm/PackageManagerShellCommand.java)。这些依据支持实现机制，不替代B真机验证。
