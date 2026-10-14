# 当前流程：顺序执行完成基线

完成节点：2026-10-14。用户确认执行流程无误。主流程20行、子流程198行；运行卡片及元素以B最终原生工程为准，本文件只登记已核对的接入和本会话常驻配置，不伪造其余卡片参数。

## 主流程

| 行 | 内容与接口 |
| --- | --- |
| 1～6 | 复用现有影刀手机连接、phone_devices及connection_infos汇总，不重建连接器 |
| 7 | start_execution(connection_infos) → 列表device_bindings；每次主流程启动只执行一次 |
| 8 | While，Python True等于True，条目外层循环 |
| 9 | prepare_devices(connection_infos) → 列表device_bindings；返回当前条目可执行设备，可能内部等待冷却/预约 |
| 10 | IF，Python len(device_bindings)==0 |
| 11 | 常驻配置：等待5到5秒，两个框为普通数值；替代此前退出当前循环 |
| 12 | End IF |
| 13 | ForEach device_bindings → device_identity，依次执行 |
| 14 | Try |
| 15 | 调用子流程1，传phone_devices[device_identity["connection_index"]]及device_identity |
| 16 | Catch device_exception |
| 17 | finish_device_error，传当前设备账号、物理设备、错误原文及当前绑定Task_ID；保留已有参数映射 |
| 18 | End Try |
| 19 | 设备循环结束 |
| 20 | 条目外层循环结束 |

20行结构来自2026-10-12配置确认；第11行常驻修改来自本会话明确指导。尚未取得修改后的原生工程导出，不把此表说成逐字段导出验证。

## 子流程关键接入

| 行或范围 | 已核对内容 |
| --- | --- |
| 5 | executed_actions初值为Python task_data.get("action_results", []) |
| 8 | 原APP启动后的等待 |
| 9～15 | 原7行回“首页——推荐”循环整体移到启动等待之后；末尾不保留重复段、不加次数上限 |
| 121 | prepare_interactions(task_data) → interaction_plan，任意类型，返回剩余动作 |
| 122 | 原动作ForEach循环；没有第二处清空executed_actions |
| 130 / 159 / 171 / 187 | Like / Comment / Favorite / Share四处record_action_result传task_data；返回累计executed_actions |
| 195～198 | Catch exception；原日志；finish_device_error(sender_account_id, physical_device_id, str(exception), device_identity["task_id"]) → 字典device_error_result；End Try |

搜索、栏目切换、筛选、作者昵称/抖音号核验及手机互动全部沿用已验证工程。点赞、评论、收藏各按成功记1；分享沿用原计划、固定分享目标规则。续发承接保存的动作、评论和设备，不重新随机分配或重复成功动作。

## 条目与设备的关系

正常执行时同条目的设备依次完成后再切换后续条目；当前是顺序执行，没有多手机同时操作。异常隔离接口保留原设计，不为归档增加自动重试或新恢复层。

冷却从单台设备完成时起算。如果A冷却5分钟，其余设备又运行20分钟才结束整条，则下一条轮到A时无需再等5分钟。若冷却未到期，第9行等待剩余时间；不必等所有设备都冷却完才执行下一条已有可用设备。
