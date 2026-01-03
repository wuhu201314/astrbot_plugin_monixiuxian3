# managers/tribulation_manager.py
"""天劫系统管理器 - 高境界突破时触发天劫"""
import random
import time
from typing import Tuple, Optional, Dict, List
from ..data import DataBase
from ..models import Player

__all__ = ["TribulationManager"]

# 天劫配置
TRIBULATION_CONFIG = {
    # 从金丹期开始触发天劫 (level_index >= 13)
    "trigger_level": 13,
    # 天劫类型
    "types": {
        "thunder": {
            "name": "雷劫",
            "description": "九天神雷降临",
            "base_damage_ratio": 0.3,  # 基础伤害为最大灵气/气血的30%
            "waves": [3, 6, 9],  # 三六九道天雷
        },
        "fire": {
            "name": "火劫",
            "description": "三昧真火焚身",
            "base_damage_ratio": 0.25,
            "waves": [3, 5, 7],
        },
        "wind": {
            "name": "风劫",
            "description": "罡风裂体",
            "base_damage_ratio": 0.2,
            "waves": [4, 7, 10],
        },
        "heart": {
            "name": "心劫",
            "description": "心魔入侵",
            "base_damage_ratio": 0.35,
            "waves": [2, 4, 6],
        },
    },
    # 境界对应的天劫难度倍率
    "difficulty_multiplier": {
        13: 1.0,   # 金丹期初期
        14: 1.1,
        15: 1.2,
        16: 1.5,   # 元婴期初期
        17: 1.7,
        18: 2.0,
        19: 2.5,   # 化神期初期
        20: 3.0,
        21: 3.5,
        22: 4.0,   # 炼虚期初期
        23: 5.0,
        24: 6.0,
        25: 8.0,   # 合体期初期
        26: 10.0,
        27: 12.0,
        28: 15.0,  # 大乘期初期
        29: 20.0,
        30: 25.0,
        31: 30.0,  # 渡劫期
        32: 50.0,  # 地仙
        33: 80.0,  # 天仙
        34: 100.0, # 大罗金仙
        35: 150.0, # 混元大罗金仙
    },
    # 渡劫成功奖励
    "success_rewards": {
        "exp_bonus_ratio": 0.1,      # 额外10%修为奖励
        "lifespan_bonus": 100,       # 额外寿命
        "attribute_bonus_ratio": 0.05,  # 属性额外提升5%
    },
    # 渡劫失败惩罚
    "failure_penalty": {
        "exp_loss_ratio": 0.2,       # 损失20%修为
        "injury_duration": 3600,      # 重伤状态持续1小时
    }
}


class TribulationManager:
    """天劫管理器"""
    
    def __init__(self, db: DataBase, config_manager=None):
        self.db = db
        self.config_manager = config_manager
    
    def should_trigger_tribulation(self, player: Player, target_level: int) -> bool:
        """判断是否应该触发天劫"""
        return target_level >= TRIBULATION_CONFIG["trigger_level"]
    
    def get_tribulation_type(self, player: Player) -> Dict:
        """根据玩家属性随机选择天劫类型"""
        types = TRIBULATION_CONFIG["types"]
        
        # 根据灵根增加特定天劫概率
        weights = {"thunder": 30, "fire": 25, "wind": 25, "heart": 20}
        
        root = player.spiritual_root
        if "雷" in root:
            weights["thunder"] += 20
        elif "火" in root:
            weights["fire"] += 20
        elif "风" in root:
            weights["wind"] += 20
        
        # 体修更容易触发心劫
        if player.cultivation_type == "体修":
            weights["heart"] += 15
        
        # 加权随机选择
        total = sum(weights.values())
        roll = random.randint(1, total)
        cumulative = 0
        
        for trib_type, weight in weights.items():
            cumulative += weight
            if roll <= cumulative:
                return {"type": trib_type, **types[trib_type]}
        
        return {"type": "thunder", **types["thunder"]}
    
    def calculate_tribulation_damage(self, player: Player, trib_type: Dict, wave: int, target_level: int) -> int:
        """计算天劫伤害"""
        base_ratio = trib_type["base_damage_ratio"]
        difficulty = TRIBULATION_CONFIG["difficulty_multiplier"].get(target_level, 1.0)
        
        # 基础伤害值
        if player.cultivation_type == "体修":
            base_value = player.max_blood_qi
        else:
            base_value = player.max_spiritual_qi
        
        # 每道天雷的伤害
        damage = int(base_value * base_ratio * difficulty * (1 + wave * 0.1))
        
        # 随机波动 ±20%
        damage = int(damage * random.uniform(0.8, 1.2))
        
        return max(1, damage)
    
    def calculate_resistance(self, player: Player) -> int:
        """计算玩家的天劫抵抗值"""
        # 基础抵抗 = 物防 + 法防 + 精神力/10
        base_resist = player.physical_defense + player.magic_defense + player.mental_power // 10
        
        # 体修额外抵抗
        if player.cultivation_type == "体修":
            base_resist += player.max_blood_qi // 100
        
        return base_resist
    
    async def execute_tribulation(self, player: Player, target_level: int) -> Tuple[bool, str, Dict]:
        """执行天劫
        
        Returns:
            (是否成功渡劫, 消息, 详细结果)
        """
        trib_type = self.get_tribulation_type(player)
        waves = trib_type["waves"]
        total_waves = waves[-1]  # 最大波数
        
        # 根据境界决定实际波数
        level_diff = target_level - TRIBULATION_CONFIG["trigger_level"]
        wave_index = min(level_diff // 5, len(waves) - 1)
        actual_waves = waves[wave_index]
        
        resistance = self.calculate_resistance(player)
        
        # 记录战斗过程
        battle_log = []
        total_damage_taken = 0
        current_hp = player.max_blood_qi if player.cultivation_type == "体修" else player.max_spiritual_qi
        
        battle_log.append(f"⚡ {trib_type['name']}降临！")
        battle_log.append(f"📜 {trib_type['description']}")
        battle_log.append(f"🌩️ 共{actual_waves}道天劫")
        battle_log.append("━━━━━━━━━━━━━━━")
        
        survived_waves = 0
        
        for wave in range(1, actual_waves + 1):
            damage = self.calculate_tribulation_damage(player, trib_type, wave, target_level)
            
            # 抵抗减伤
            actual_damage = max(1, damage - resistance // (wave + 1))
            
            # 随机触发完美抵抗（5%概率）
            if random.random() < 0.05:
                actual_damage = actual_damage // 2
                battle_log.append(f"第{wave}道：完美抵抗！伤害减半 (-{actual_damage})")
            else:
                battle_log.append(f"第{wave}道：承受伤害 -{actual_damage}")
            
            total_damage_taken += actual_damage
            current_hp -= actual_damage
            
            if current_hp <= 0:
                battle_log.append(f"💀 第{wave}道天劫未能抵挡...")
                break
            
            survived_waves = wave
        
        # 判定结果
        success = survived_waves >= actual_waves
        
        result = {
            "tribulation_type": trib_type["name"],
            "total_waves": actual_waves,
            "survived_waves": survived_waves,
            "total_damage": total_damage_taken,
            "success": success,
        }
        
        if success:
            # 渡劫成功奖励
            rewards = TRIBULATION_CONFIG["success_rewards"]
            exp_bonus = int(player.experience * rewards["exp_bonus_ratio"])
            lifespan_bonus = rewards["lifespan_bonus"]
            
            player.experience += exp_bonus
            player.lifespan += lifespan_bonus
            
            # 属性小幅提升
            attr_bonus = rewards["attribute_bonus_ratio"]
            player.physical_damage = int(player.physical_damage * (1 + attr_bonus))
            player.magic_damage = int(player.magic_damage * (1 + attr_bonus))
            player.physical_defense = int(player.physical_defense * (1 + attr_bonus))
            player.magic_defense = int(player.magic_defense * (1 + attr_bonus))
            
            await self.db.update_player(player)
            
            battle_log.append("━━━━━━━━━━━━━━━")
            battle_log.append("✨ 渡劫成功！")
            battle_log.append(f"🎁 额外修为：+{exp_bonus:,}")
            battle_log.append(f"💫 额外寿命：+{lifespan_bonus}")
            battle_log.append(f"📈 属性提升：+{attr_bonus:.0%}")
            
            result["exp_bonus"] = exp_bonus
            result["lifespan_bonus"] = lifespan_bonus
        else:
            # 渡劫失败惩罚
            penalty = TRIBULATION_CONFIG["failure_penalty"]
            exp_loss = int(player.experience * penalty["exp_loss_ratio"])
            player.experience = max(0, player.experience - exp_loss)
            
            await self.db.update_player(player)
            
            battle_log.append("━━━━━━━━━━━━━━━")
            battle_log.append("💔 渡劫失败！")
            battle_log.append(f"📉 损失修为：-{exp_loss:,}")
            battle_log.append("⚠️ 身受重伤，需要休养")
            
            result["exp_loss"] = exp_loss
        
        return success, "\n".join(battle_log), result
    
    def get_tribulation_preview(self, player: Player, target_level: int) -> str:
        """获取天劫预览信息"""
        if not self.should_trigger_tribulation(player, target_level):
            return ""
        
        difficulty = TRIBULATION_CONFIG["difficulty_multiplier"].get(target_level, 1.0)
        resistance = self.calculate_resistance(player)
        
        # 估算生存概率
        if player.cultivation_type == "体修":
            hp_ratio = player.max_blood_qi / (player.max_blood_qi * 0.3 * difficulty * 5)
        else:
            hp_ratio = player.max_spiritual_qi / (player.max_spiritual_qi * 0.3 * difficulty * 5)
        
        survival_chance = min(95, max(5, int(hp_ratio * 100 * (1 + resistance / 10000))))
        
        return (
            f"\n⚡ 天劫预警 ⚡\n"
            f"难度系数：{difficulty:.1f}x\n"
            f"你的抗性：{resistance:,}\n"
            f"预估成功率：约{survival_chance}%\n"
            f"💡 提升防御和精神力可增加渡劫成功率"
        )
