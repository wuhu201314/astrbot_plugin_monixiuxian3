# managers/inner_demon_manager.py
"""心魔系统管理器 - 修炼过程中的心魔挑战"""
import random
import time
from typing import Tuple, Optional, Dict, List
from ..data import DataBase
from ..models import Player

__all__ = ["InnerDemonManager"]

# 心魔配置
INNER_DEMON_CONFIG = {
    # 心魔触发概率（闭关时）
    "trigger_chance": 0.10,  # 10%
    # 心魔类型
    "types": {
        "greed": {
            "name": "贪念心魔",
            "description": "对灵石财富的执念化为心魔",
            "question": "你看到无尽的灵石堆积如山，是否要全部据为己有？",
            "correct_choice": "放下",
            "wrong_penalty": {"gold": 0.1},  # 损失10%灵石
            "success_reward": {"mental_power": 10},
            "weight": 30,
        },
        "anger": {
            "name": "嗔怒心魔",
            "description": "过往的仇恨化为心魔",
            "question": "仇人就在眼前，你是否要出手报仇？",
            "correct_choice": "放下",
            "wrong_penalty": {"exp": 0.05},  # 损失5%修为
            "success_reward": {"mental_power": 15},
            "weight": 25,
        },
        "obsession": {
            "name": "执念心魔",
            "description": "对力量的渴望化为心魔",
            "question": "眼前出现一条捷径可以快速提升实力，但需要牺牲寿元，是否接受？",
            "correct_choice": "拒绝",
            "wrong_penalty": {"lifespan": 50},  # 损失50寿元
            "success_reward": {"mental_power": 20},
            "weight": 20,
        },
        "fear": {
            "name": "恐惧心魔",
            "description": "对死亡的恐惧化为心魔",
            "question": "你陷入无尽的黑暗，感受到死亡的气息，是否要逃离？",
            "correct_choice": "面对",
            "wrong_penalty": {"qi": 0.3},  # 损失30%灵气/气血
            "success_reward": {"mental_power": 25, "physical_defense": 5, "magic_defense": 5},
            "weight": 15,
        },
        "illusion": {
            "name": "幻境心魔",
            "description": "虚幻的美好化为心魔",
            "question": "你看到了理想中的世界，一切都如此美好，是否要留在这里？",
            "correct_choice": "离开",
            "wrong_penalty": {"exp": 0.1, "mental_power": 10},
            "success_reward": {"mental_power": 30, "exp_bonus": 500},
            "weight": 10,
        },
    },
    # 心魔冷却时间（秒）
    "cooldown": 7200,  # 2小时
    # 境界影响心魔强度
    "level_multiplier": {
        "penalty": 0.05,  # 每10级惩罚增加5%
        "reward": 0.1,    # 每10级奖励增加10%
    },
}

# 心魔对话
DEMON_DIALOGUES = {
    "appear": [
        "一道黑影从你的识海中浮现...",
        "你感到一股邪念在心中滋生...",
        "修炼中，你的心魔突然显现...",
        "一个熟悉又陌生的声音在耳边响起...",
    ],
    "success": [
        "心魔消散，道心更加坚定！",
        "你战胜了内心的魔障！",
        "心如明镜，不染尘埃。",
        "道心通明，心魔退散！",
    ],
    "failure": [
        "心魔趁虚而入，你受到了反噬...",
        "一时迷失，付出了代价...",
        "心魔得逞，你损失惨重...",
        "道心动摇，遭受惩罚...",
    ],
}


class InnerDemonManager:
    """心魔管理器"""
    
    def __init__(self, db: DataBase, config_manager=None):
        self.db = db
        self.config_manager = config_manager
        self._last_demon: Dict[str, int] = {}  # 记录玩家上次心魔时间
        self._pending_demons: Dict[str, Dict] = {}  # 待处理的心魔
    
    def _check_cooldown(self, player: Player) -> bool:
        """检查心魔冷却"""
        last_time = self._last_demon.get(player.user_id, 0)
        return time.time() - last_time >= INNER_DEMON_CONFIG["cooldown"]
    
    def _select_demon_type(self, player: Player) -> Dict:
        """选择心魔类型"""
        types = INNER_DEMON_CONFIG["types"]
        
        # 加权随机选择
        total = sum(t["weight"] for t in types.values())
        roll = random.randint(1, total)
        cumulative = 0
        
        for dtype, demon in types.items():
            cumulative += demon["weight"]
            if roll <= cumulative:
                return {"type": dtype, **demon}
        
        return {"type": "greed", **types["greed"]}
    
    def _calculate_penalty_multiplier(self, player: Player) -> float:
        """计算惩罚倍率"""
        base = 1.0
        level_bonus = (player.level_index // 10) * INNER_DEMON_CONFIG["level_multiplier"]["penalty"]
        return base + level_bonus
    
    def _calculate_reward_multiplier(self, player: Player) -> float:
        """计算奖励倍率"""
        base = 1.0
        level_bonus = (player.level_index // 10) * INNER_DEMON_CONFIG["level_multiplier"]["reward"]
        return base + level_bonus
    
    async def try_trigger_demon(self, player: Player) -> Tuple[bool, str, Optional[Dict]]:
        """尝试触发心魔
        
        Returns:
            (是否触发, 消息, 心魔数据)
        """
        # 检查冷却
        if not self._check_cooldown(player):
            return False, "", None
        
        # 检查触发概率
        if random.random() > INNER_DEMON_CONFIG["trigger_chance"]:
            return False, "", None
        
        # 选择心魔类型
        demon = self._select_demon_type(player)
        
        # 记录待处理心魔
        self._pending_demons[player.user_id] = {
            "demon": demon,
            "triggered_at": int(time.time()),
        }
        
        # 构建消息
        appear_msg = random.choice(DEMON_DIALOGUES["appear"])
        msg = (
            f"👿 心魔来袭！👿\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{appear_msg}\n"
            f"\n【{demon['name']}】\n"
            f"📜 {demon['description']}\n"
            f"\n❓ {demon['question']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💡 请在30秒内回复选择：\n"
            f"• 发送「{demon['correct_choice']}」或「抵抗」\n"
            f"• 发送「接受」或「屈服」\n"
            f"⚠️ 超时或选择错误将受到惩罚！"
        )
        
        return True, msg, demon
    
    async def respond_to_demon(self, player: Player, choice: str) -> Tuple[bool, str]:
        """响应心魔
        
        Args:
            player: 玩家对象
            choice: 玩家选择
            
        Returns:
            (是否成功抵抗, 消息)
        """
        pending = self._pending_demons.get(player.user_id)
        if not pending:
            return False, "你当前没有需要应对的心魔。"
        
        demon = pending["demon"]
        triggered_at = pending["triggered_at"]
        
        # 检查是否超时（30秒）
        if time.time() - triggered_at > 30:
            del self._pending_demons[player.user_id]
            # 超时视为失败
            penalty_msg = await self._apply_penalty(player, demon)
            fail_msg = random.choice(DEMON_DIALOGUES["failure"])
            return False, (
                f"⏰ 心魔应对超时！\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{fail_msg}\n"
                f"{penalty_msg}"
            )
        
        # 清除待处理心魔
        del self._pending_demons[player.user_id]
        self._last_demon[player.user_id] = int(time.time())
        
        # 判断选择是否正确
        correct_choices = [demon["correct_choice"], "抵抗"]
        wrong_choices = ["接受", "屈服"]
        
        choice_lower = choice.strip()
        
        if choice_lower in correct_choices:
            # 成功抵抗
            reward_msg = await self._apply_reward(player, demon)
            success_msg = random.choice(DEMON_DIALOGUES["success"])
            return True, (
                f"✨ 心魔退散！✨\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{success_msg}\n"
                f"{reward_msg}"
            )
        elif choice_lower in wrong_choices:
            # 屈服于心魔
            penalty_msg = await self._apply_penalty(player, demon)
            fail_msg = random.choice(DEMON_DIALOGUES["failure"])
            return False, (
                f"💔 心魔得逞！💔\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{fail_msg}\n"
                f"{penalty_msg}"
            )
        else:
            # 无效选择，给予提示
            return False, (
                f"❓ 无效的选择！\n"
                f"请回复「{demon['correct_choice']}」「抵抗」或「接受」「屈服」"
            )
    
    async def _apply_penalty(self, player: Player, demon: Dict) -> str:
        """应用心魔惩罚"""
        penalty = demon["wrong_penalty"]
        multiplier = self._calculate_penalty_multiplier(player)
        penalty_lines = ["📉 惩罚："]
        
        if "gold" in penalty:
            amount = int(player.gold * penalty["gold"] * multiplier)
            player.gold = max(0, player.gold - amount)
            penalty_lines.append(f"  灵石 -{amount:,}")
        
        if "exp" in penalty:
            amount = int(player.experience * penalty["exp"] * multiplier)
            player.experience = max(0, player.experience - amount)
            penalty_lines.append(f"  修为 -{amount:,}")
        
        if "lifespan" in penalty:
            amount = int(penalty["lifespan"] * multiplier)
            player.lifespan = max(1, player.lifespan - amount)
            penalty_lines.append(f"  寿元 -{amount}")
        
        if "qi" in penalty:
            if player.cultivation_type == "体修":
                amount = int(player.blood_qi * penalty["qi"] * multiplier)
                player.blood_qi = max(0, player.blood_qi - amount)
                penalty_lines.append(f"  气血 -{amount:,}")
            else:
                amount = int(player.spiritual_qi * penalty["qi"] * multiplier)
                player.spiritual_qi = max(0, player.spiritual_qi - amount)
                penalty_lines.append(f"  灵气 -{amount:,}")
        
        if "mental_power" in penalty:
            amount = int(penalty["mental_power"] * multiplier)
            player.mental_power = max(0, player.mental_power - amount)
            penalty_lines.append(f"  精神力 -{amount}")
        
        await self.db.update_player(player)
        return "\n".join(penalty_lines)
    
    async def _apply_reward(self, player: Player, demon: Dict) -> str:
        """应用心魔奖励"""
        reward = demon["success_reward"]
        multiplier = self._calculate_reward_multiplier(player)
        reward_lines = ["🎁 奖励："]
        
        if "mental_power" in reward:
            amount = int(reward["mental_power"] * multiplier)
            player.mental_power += amount
            reward_lines.append(f"  精神力 +{amount}")
        
        if "physical_defense" in reward:
            amount = int(reward["physical_defense"] * multiplier)
            player.physical_defense += amount
            reward_lines.append(f"  物防 +{amount}")
        
        if "magic_defense" in reward:
            amount = int(reward["magic_defense"] * multiplier)
            player.magic_defense += amount
            reward_lines.append(f"  法防 +{amount}")
        
        if "exp_bonus" in reward:
            amount = int(reward["exp_bonus"] * multiplier)
            player.experience += amount
            reward_lines.append(f"  修为 +{amount:,}")
        
        await self.db.update_player(player)
        return "\n".join(reward_lines)
    
    def has_pending_demon(self, player: Player) -> bool:
        """检查是否有待处理的心魔"""
        return player.user_id in self._pending_demons
    
    def get_demon_info(self, player: Player) -> str:
        """获取心魔信息"""
        cooldown_remaining = 0
        last_time = self._last_demon.get(player.user_id, 0)
        if last_time > 0:
            elapsed = time.time() - last_time
            cooldown_remaining = max(0, INNER_DEMON_CONFIG["cooldown"] - elapsed)
        
        info = (
            f"👿 心魔信息\n"
            f"━━━━━━━━━━━━━━━\n"
            f"触发概率：{INNER_DEMON_CONFIG['trigger_chance']:.0%}\n"
            f"精神力：{player.mental_power:,}\n"
        )
        
        if cooldown_remaining > 0:
            minutes = int(cooldown_remaining // 60)
            info += f"冷却剩余：{minutes}分钟\n"
        else:
            info += f"状态：可能触发心魔\n"
        
        info += (
            f"\n【心魔类型】\n"
            f"• 贪念心魔：对财富的执念\n"
            f"• 嗔怒心魔：对仇恨的执念\n"
            f"• 执念心魔：对力量的渴望\n"
            f"• 恐惧心魔：对死亡的恐惧\n"
            f"• 幻境心魔：对虚幻的沉迷\n"
            f"\n💡 提升精神力可更好地抵抗心魔\n"
            f"💡 成功抵抗心魔可获得奖励"
        )
        
        return info
