# managers/fortune_manager.py
"""福缘系统管理器 - 随机福缘事件"""
import random
import time
from typing import Tuple, Optional, Dict, List
from ..data import DataBase
from ..models import Player

__all__ = ["FortuneManager"]

# 福缘配置
FORTUNE_CONFIG = {
    # 福缘事件类型
    "events": {
        "spirit_stone_rain": {
            "name": "灵石雨",
            "description": "天降灵石，福缘深厚",
            "reward_type": "gold",
            "reward_range": [100, 500],
            "weight": 40,
        },
        "ancient_inheritance": {
            "name": "古人遗泽",
            "description": "偶得前辈遗留的修炼心得",
            "reward_type": "exp",
            "reward_range": [500, 2000],
            "weight": 30,
        },
        "spirit_spring": {
            "name": "灵泉涌现",
            "description": "发现一处灵泉，灵气充沛",
            "reward_type": "qi",
            "reward_ratio": 0.5,  # 恢复50%灵气/气血
            "weight": 20,
        },
        "lifespan_blessing": {
            "name": "天赐寿元",
            "description": "福缘深厚，寿元增长",
            "reward_type": "lifespan",
            "reward_range": [10, 50],
            "weight": 8,
        },
        "divine_artifact": {
            "name": "神器认主",
            "description": "一件神秘法器认你为主",
            "reward_type": "attribute",
            "attribute_bonus": {
                "physical_damage": [5, 20],
                "magic_damage": [5, 20],
                "physical_defense": [3, 15],
                "magic_defense": [3, 15],
            },
            "weight": 2,
        },
    },
    # 每日福缘次数上限
    "daily_limit": 3,
    # 福缘触发概率（每次操作）
    "trigger_chance": 0.08,  # 8%
}

# 福缘语录
FORTUNE_QUOTES = [
    "福兮祸所伏，祸兮福所倚。",
    "天道酬勤，福缘自来。",
    "积善之家，必有余庆。",
    "机缘巧合，造化弄人。",
    "冥冥之中，自有天意。",
]


class FortuneManager:
    """福缘管理器"""
    
    def __init__(self, db: DataBase, config_manager=None):
        self.db = db
        self.config_manager = config_manager
        self._daily_fortune_count: Dict[str, Dict] = {}  # {user_id: {date: count}}
    
    def _get_today_key(self) -> str:
        """获取今日日期键"""
        return time.strftime("%Y-%m-%d")
    
    def _get_daily_count(self, user_id: str) -> int:
        """获取今日福缘次数"""
        today = self._get_today_key()
        user_data = self._daily_fortune_count.get(user_id, {})
        return user_data.get(today, 0)
    
    def _increment_daily_count(self, user_id: str):
        """增加今日福缘次数"""
        today = self._get_today_key()
        if user_id not in self._daily_fortune_count:
            self._daily_fortune_count[user_id] = {}
        self._daily_fortune_count[user_id] = {today: self._get_daily_count(user_id) + 1}
    
    def _select_fortune_event(self) -> Dict:
        """选择福缘事件"""
        events = FORTUNE_CONFIG["events"]
        
        # 加权随机选择
        total = sum(e["weight"] for e in events.values())
        roll = random.randint(1, total)
        cumulative = 0
        
        for etype, event in events.items():
            cumulative += event["weight"]
            if roll <= cumulative:
                return {"type": etype, **event}
        
        return {"type": "spirit_stone_rain", **events["spirit_stone_rain"]}
    
    async def try_fortune(self, player: Player, action: str = "general") -> Tuple[bool, str]:
        """尝试触发福缘事件
        
        Args:
            player: 玩家对象
            action: 触发动作类型
            
        Returns:
            (是否触发, 消息)
        """
        # 检查每日次数
        if self._get_daily_count(player.user_id) >= FORTUNE_CONFIG["daily_limit"]:
            return False, ""
        
        # 检查触发概率
        if random.random() > FORTUNE_CONFIG["trigger_chance"]:
            return False, ""
        
        # 选择福缘事件
        event = self._select_fortune_event()
        
        # 处理奖励
        reward_msg = await self._apply_fortune_reward(player, event)
        
        # 增加计数
        self._increment_daily_count(player.user_id)
        
        # 构建消息
        quote = random.choice(FORTUNE_QUOTES)
        msg = (
            f"🍀 福缘降临！🍀\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✨ {event['name']}\n"
            f"📜 {event['description']}\n"
            f"「{quote}」\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{reward_msg}"
        )
        
        return True, msg
    
    async def _apply_fortune_reward(self, player: Player, event: Dict) -> str:
        """应用福缘奖励"""
        reward_type = event["reward_type"]
        reward_msg = ""
        
        if reward_type == "gold":
            amount = random.randint(*event["reward_range"])
            player.gold += amount
            reward_msg = f"💰 获得灵石：+{amount:,}"
            
        elif reward_type == "exp":
            amount = random.randint(*event["reward_range"])
            # 根据境界调整
            amount = int(amount * (1 + player.level_index * 0.1))
            player.experience += amount
            reward_msg = f"📈 获得修为：+{amount:,}"
            
        elif reward_type == "qi":
            ratio = event["reward_ratio"]
            if player.cultivation_type == "体修":
                amount = int(player.max_blood_qi * ratio)
                player.blood_qi = min(player.max_blood_qi, player.blood_qi + amount)
                reward_msg = f"💪 恢复气血：+{amount:,}"
            else:
                amount = int(player.max_spiritual_qi * ratio)
                player.spiritual_qi = min(player.max_spiritual_qi, player.spiritual_qi + amount)
                reward_msg = f"✨ 恢复灵气：+{amount:,}"
                
        elif reward_type == "lifespan":
            amount = random.randint(*event["reward_range"])
            player.lifespan += amount
            reward_msg = f"💫 增加寿元：+{amount}"
            
        elif reward_type == "attribute":
            bonuses = event["attribute_bonus"]
            reward_lines = ["🎁 属性提升："]
            
            for attr, range_val in bonuses.items():
                amount = random.randint(*range_val)
                current = getattr(player, attr, 0)
                setattr(player, attr, current + amount)
                
                attr_names = {
                    "physical_damage": "物伤",
                    "magic_damage": "法伤",
                    "physical_defense": "物防",
                    "magic_defense": "法防",
                }
                reward_lines.append(f"  {attr_names.get(attr, attr)} +{amount}")
            
            reward_msg = "\n".join(reward_lines)
        
        await self.db.update_player(player)
        return reward_msg
    
    async def claim_daily_fortune(self, player: Player) -> Tuple[bool, str]:
        """领取每日福缘（主动触发）
        
        Returns:
            (是否成功, 消息)
        """
        # 检查每日次数
        daily_count = self._get_daily_count(player.user_id)
        if daily_count >= FORTUNE_CONFIG["daily_limit"]:
            return False, f"今日福缘已用尽（{daily_count}/{FORTUNE_CONFIG['daily_limit']}），明日再来！"
        
        # 直接触发福缘
        event = self._select_fortune_event()
        reward_msg = await self._apply_fortune_reward(player, event)
        self._increment_daily_count(player.user_id)
        
        remaining = FORTUNE_CONFIG["daily_limit"] - self._get_daily_count(player.user_id)
        
        quote = random.choice(FORTUNE_QUOTES)
        msg = (
            f"🍀 福缘降临！🍀\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✨ {event['name']}\n"
            f"📜 {event['description']}\n"
            f"「{quote}」\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{reward_msg}\n"
            f"\n今日剩余福缘次数：{remaining}"
        )
        
        return True, msg
    
    def get_fortune_info(self, player: Player) -> str:
        """获取福缘信息"""
        daily_count = self._get_daily_count(player.user_id)
        remaining = FORTUNE_CONFIG["daily_limit"] - daily_count
        
        info = (
            f"🍀 福缘信息\n"
            f"━━━━━━━━━━━━━━━\n"
            f"今日已触发：{daily_count}次\n"
            f"今日剩余：{remaining}次\n"
            f"触发概率：{FORTUNE_CONFIG['trigger_chance']:.0%}\n"
            f"\n【福缘类型】\n"
        )
        
        for etype, event in FORTUNE_CONFIG["events"].items():
            info += f"• {event['name']}：{event['description']}\n"
        
        info += f"\n💡 使用 /求福缘 可主动触发福缘"
        
        return info
