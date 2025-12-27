# Codex全局工作指南

## 回答风格:
 - 回答必须使用中文
 - 对总结、Plan、Task、以及长内容的输出，优先进行逻辑整理后使用美观的Table格式整齐输出;普通内容正常输出

## 工具使用:
1. 文件与代码检索:使用serena mcp来进行文件与代码的检索
2. 文件相关操作:对文件的创建、读取、编辑、删除等操作
    - 优先使用apply_patch工具进行
    - 读文件，apply_patch工具报错或出现问题的情况下使用desktop-commander mcp
    - 任何情况下，禁止使用cmd、powershell或者python来进行文件相关操作


本项目的情况

📊 模拟修仙 v2 插件系统总结
一、系统总览
分类	系统数量	说明
核心玩法	8 个	游戏基础核心机制
独有特色	4 个	插件独创玩法
辅助系统	8 个	支撑性功能系统
总计	20 个系统	-
二、详细系统列表
🎮 核心玩法系统 (8个)
系统名称	Handler文件	Manager文件	核心功能
境界修炼	player_handler.py	cultivation_manager.py	闭关/出关，九大境界突破
突破系统	breakthrough_handler.py	breakthrough_manager.py	境界突破、成功率计算
战斗系统	combat_handlers.py	combat_manager.py	PVP切磋/决斗，HP/MP/ATK计算
宗门系统	sect_handlers.py	sect_manager.py	创建/加入宗门，职位管理
世界Boss	boss_handlers.py	boss_manager.py	全服Boss讨伐，伤害排名
秘境探索	rift_handlers.py	rift_manager.py	挂机式秘境探险
历练系统	adventure_handlers.py	adventure_manager.py	离线挂机，短/中/长途
炼丹系统	alchemy_handlers.py	alchemy_manager.py	配方炼制丹药
✨ 独有特色系统 (4个)
系统名称	Handler文件	Manager文件	核心功能
🏔️ 洞天福地	blessed_land_handlers.py	blessed_land_manager.py	5档洞天，持续产出灵石修为
🌾 灵田种植	spirit_farm_handlers.py	spirit_farm_manager.py	开垦灵田，5种灵草种植
💕 双修系统	dual_cultivation_handlers.py	dual_cultivation_manager.py	双方互增10%修为
👁️ 天地灵眼	spirit_eye_handlers.py	spirit_eye_manager.py	抢占灵眼PVP资源争夺
🔧 辅助功能系统 (8个)
系统名称	Handler文件	Manager/Core文件	核心功能
装备系统	equipment_handler.py	equipment_manager.py	武器/防具/心法装备
丹药系统	pill_handler.py	pill_manager.py	丹药使用与效果
商店系统	shop_handler.py	shop_manager.py	丹阁/器阁/百宝阁
储物戒	storage_ring_handler.py	core/storage_ring_manager.py	物品存储管理（中央枢纽）
灵石银行	bank_handlers.py	bank_manager.py	存取灵石，5%年利率
悬赏任务	bounty_handlers.py	bounty_manager.py	接取/完成悬赏任务
传承系统	impart_handlers.py + impart_pk_handlers.py	impart_manager.py + impart_pk_manager.py	传承挑战与Buff加成
排行榜	ranking_handlers.py	ranking_manager.py	境界/战力/灵石/宗门榜
三、代码架构统计
目录	文件数	职责
handlers/	24 个	指令处理器（用户交互层）
managers/	16 个	业务逻辑管理器
core/	7 个	核心功能模块
data/	5 个	数据管理与持久化
config/	4+ 个	配置文件

四、v2.6.0 更新日志 - 突破系统完善

🎯 核心改造：突破丹药体系重构，全境界覆盖

💊 专属破境丹完善（pills.json）
| 新增丹药 | 目标境界 | 加成效果 |
|---------|----------|---------|
| 固基丹·中/后 | 筑基期内部突破 | +50%/+60% |
| 温丹丹·中/后 | 金丹期内部突破 | +70%/+72% |
| 养婴丹·中/后 | 元婴期内部突破 | +76%/+74% |
| 温神丹·中/后 | 化神期内部突破 | +77%/+78% |
| 破虚丹·中/后 | 炼虚期内部突破 | +79%/+77% |
| 融合丹·中/后 | 合体期内部突破 | +72%/+70% |
| 悟道丹·中/后 | 大乘期内部突破 | +62%/+58% |
| 混元丹 | 混元大罗金仙 | +5% |

🔄 通用增益丹改名（items.json）
| 原名称 | 新名称 | 效果 |
|-------|--------|------|
| 三品筑基丹 | 三品凝神增益丹 | 通用+10%突破率(1小时) |
| 四品破境丹 | 四品破境增益丹 | 通用+15%突破率(1小时) |
| 五品渡劫丹 | 五品渡劫增益丹 | 通用+20%突破率(1小时) |
| 六品破婴丹 | 六品破境增益丹 | 通用+25%突破率(1小时) |
| 七品化神丹 | 七品化神增益丹 | 通用+30%突破率(1小时) |
| 八品破虚丹 | 八品破虚增益丹 | 通用+35%突破率(1小时) |
| 九品破劫丹 | 九品破劫增益丹 | 通用+50%突破率(1小时) |
| 焚天逆命丹 | 焚天逆命增益丹 | 通用+18%突破率(有副作用) |

🌀 秘境稀有丹药掉落（rift_manager.py）
| 秘境等级 | 掉落概率 | 可掉落丹药 |
|----------|----------|-----------|
| 低级秘境 | 3% | 三品凝神增益丹 |
| 中级秘境 | 5% | 三/四/五品增益丹 |
| 高级秘境 | 10% | 四/五/六/七品增益丹 |

🔧 修复问题
- 修复items.json中`add_breakthrough_bonus`未生效的问题
- 通用增益丹购买后正确添加1小时临时突破加成效果
- 明确区分"专属破境丹"(境界限制)与"通用增益丹"(无限制)

五、v2.5.0 更新日志 - 储物戒系统重构

🎯 核心改造：储物戒成为游戏物品流转的中央枢纽

📦 系统联动（8个系统接入）
| 系统 | 入库场景 | 出库场景 |
|------|---------|---------| 
| 商店系统 | 购买物品→自动存入 | - |
| 装备系统 | 卸下装备→存入 | 装备→从储物戒取出 |
| 炼丹系统 | - | 炼丹→消耗储物戒材料 |
| 历练系统 | 完成历练→物品掉落 | - |
| 秘境系统 | 探索完成→物品掉落 | - |
| Boss系统 | 击杀奖励→物品掉落 | - |
| 悬赏系统 | 完成悬赏→物品奖励 | - |
| 灵田系统 | 收获灵草→存入储物戒 | - |

🆕 新增功能
- 物品分类视图：按材料/装备/功法/其他分组显示
- 物品搜索：`搜索物品 关键词` 模糊搜索
- 批量取出：`取出所有 分类` 批量操作
- 储物戒升级消耗：需支付灵石购买

🔧 修复问题
- 炼丹现在正确消耗储物戒中的灵草材料
- 装备物品必须先存在于储物戒中
- 赠予请求持久化到数据库（24小时有效期）
- 修正文档中manager文件路径记录