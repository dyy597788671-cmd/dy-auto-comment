# 版本与交付基线

更新时间：2026-10-14。完成节点：20261014-SEQUENTIAL-COMPLETE。

| 材料 | 当前基线 |
| --- | --- |
| 原核心与影刀桥接接口 | v1.1.0完整接口安装包；本次不改运行实现 |
| 网页工具 | v1.1.1设备数量修复 |
| 主/子流程 | 20 / 198行；常驻配置第11行等待 |
| 冷却示例 | templates/settings.json，300 / 600秒 |
| 最终原生工程 | 待补收B当前完整导出；旧导出不能作为最终恢复材料 |
| 源码冻结前提交 | a1056a29e5a39a963bd7b5fc3ab17b2767234b4e |

## 已保存的原安装包

| 文件 | 用途 | SHA-256 |
| --- | --- | --- |
| [DouyinTaskTool_v1.1.0_B.zip](packages/DouyinTaskTool_v1.1.0_B.zip) | 核心接口完整安装；已现场升级通过 | a5811fc690934a954ca5bd0673e1dcd631003c36dcb9f85abf1ea823bc9d12f9 |
| [DouyinTaskTool_v1.1.1_B.zip](packages/DouyinTaskTool_v1.1.1_B.zip) | 已有v1.1.0基础上的网页数量修复；现场数量验证通过 | 513185cfdd15e593765b4315f582a9f7ef483ac62ae78f8335c114b6d79b8dc4 |

两个zip保留原交付字节，不重打包为新版本。v1.1.1为web-only，不含core_runner.py和module1.py，不可替代首次完整核心安装。恢复环境时按[复用指南](REUSE_GUIDE.md)执行先完整接口、后数量修复的既定顺序。

实际B模块PROJECT_ROOT随xbot_robot/module1.py位置确定。安装器保留该前缀，不拿历史A电脑绝对路径覆盖B。主程序代码、源码API和历史证据不等同于最新原生工程导出。
