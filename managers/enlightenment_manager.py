# managers/enlightenment_manager.py
"""悟道系统管理器 - 随机悟道事件获得额外修为"""
import random
import time
from typing import Tuple, Optional, Dict
from ..data import DataBase
from ..models import Player

__all__ = ["EnlightenmentManager"]

# 悟道配置
ENLIGHTENMENT_CONFIG = {
    # 悟道触发概率（每次闭关结算时）
    "trigger_chance": 0.15,  # 15%概率触发
    # 悟道类型
    "types": {
        "minor": {
            "name": "小悟",
            "description": "灵光一闪，略有所得",
            "exp_bonus_ratio": 0.05,  # 额外5%修为
            "weight": 60,
        },
        "normal": {
            "name": "顿悟",
            "description": "心有所感，道心通明",
            "exp_bonus_ratio": 0.15,  # 额外15%修为
            "weight": 30,
        },
        "major": {
            "name": "大彻大悟",
            "description": "天地共鸣，道法自然",
            "exp_bonus_ratio": 0.30,  # 额外30%修为
            "weight": 8,
        },
        "supreme": {
            "name": "天人合一",
            "description": "与天地同寿，与日月同辉",
            "exp_bonus_ratio": 0.50,  # 额外50%修为
            "attribute_bonus": True,  # 额外属性加成
            "weight": 2,
        },
    },
    # 悟道冷却时间（秒）
    "cooldown": 3600,  # 1小时内只能触发一次
    # 精神力影响悟道概率
    "mental_power_bonus": {
        "threshold": 1000,  # 每1000精神力
        "bonus": 0.01,  # 增加1%触发概率
        "max_bonus": 0.15,  # 最多增加15%
    },
}

# 悟道语录
ENLIGHTENMENT_QUOTES = [
    "道可道，非常道。",
    "上善若水，水善利万物而不争。",
    "天地不仁，以万物为刍狗。",
    "知者不言，言者不知。",
    "大道至简，返璞归真。",
    "心若止水，万物皆空。",
    "一花一世界，一叶一菩提。",
    "无为而无不为。",
    "道生一，一生二，二生三，三生万物。",
    "致虚极，守静笃。",
]


class EnlightenmentManager:
    """悟道管理器"""
    
    def __init__(self, db: DataBase, config_manager=None):
        self.db = db
        self.config_manager = config_manager
        self._last_enlightenment: Dict[str, int] = {}  # 记录玩家上次悟道时间
    
    def _get_trigger_chance(self, player: Player) -> float:
        """计算悟道触发概率"""
        base_chance = ENLIGHTENMENT_CONFIG["trigger_chance"]
        
        # 精神力加成
        mental_config = ENLIGHTENMENT_CONFIG["mental_power_bonus"]
        mental_bonus = min(
            (player.mental_power // mental_config["threshold"]) * mental_config["bonus"],
            mental_config["max_bonus"]
        )
        
        return min(0.5, base_chance + mental_bonus)  # 最高50%
    
    def _check_cooldown(self, player: Player) -> bool:
        """检查悟道冷却"""
        last_time = self._last_enlightenment.get(player.user_id, 0)
        return time.time() - last_time >= ENLIGHTENMENT_CONFIG["cooldown"]
    
    def _select_enlightenment_type(self, player: Player) -> Dict:
        """选择悟道类型"""
        types = ENLIGHTENMENT_CONFIG["types"]
        
        # 加权随机选择
        weights = {k: v["weight"] for k, v in types.items()}
        
        # 高境界玩家更容易获得高级悟道
        if player.level_index >= 20:  # 化神期以上
            weights["major"] += 5
            weights["supreme"] += 2
        elif player.level_index >= 13:  # 金丹期以上
            weights["normal"] += 10
            weights["major"] += 3
        
        total = sum(weights.values())
        roll = random.randint(1, total)
        cumulative = 0
        
        for etype, weight in weights.items():
            cumulative += weight
            if roll <= cumulative:
                return {"type": etype, **types[etype]}
        
        return {"type": "minor", **types["minor"]}
    
    async def try_enlightenment(self, player: Player, cultivation_exp: int) -> Tuple[bool, str, int]:
        """尝试触发悟道
        
        Args:
            player: 玩家对象
            cultivation_exp: 本次闭关获得的修为
            
        Returns:
            (是否触发, 消息, 额外修为)
        """
        # 检查冷却
        if not self._check_cooldown(player):
            return False, "", 0
        
        # 检查触发概率
        trigger_chance = self._get_trigger_chance(player)
        if random.random() > trigger_chance:
            return False, "", 0
        
        # 选择悟道类型
        enlightenment = self._select_enlightenment_type(player)
        
        # 计算额外修为
        bonus_exp = int(cultivation_exp * enlightenment["exp_bonus_ratio"])
        
        # 记录悟道时间
        self._last_enlightenment[player.user_id] = int(time.time())
        
        # 构建消息
        quote = random.choice(ENLIGHTENMENT_QUOTES)
        msg_lines = [
            f"💫 {enlightenment['name']}！💫",
            f"━━━━━━━━━━━━━━━",
            f"「{quote}」",
            f"",
            f"📜 {enlightenment['description']}",
            f"✨ 额外获得修为：+{bonus_exp:,}",
        ]
        
        # 天人合一额外奖励
        if enlightenment.get("attribute_bonus"):
            attr_bonus = max(1, player.mental_power // 100)
            player.mental_power += attr_bonus
            player.physical_defense += attr_bonus // 2
            player.magic_defense += attr_bonus // 2
            await self.db.update_player(player)
            
            msg_lines.extend([
                f"",
                f"🌟 天人合一特殊奖励：",
                f"精神力 +{attr_bonus}",
                f"物防/法防 +{attr_bonus // 2}",
            ])
        
        return True, "\n".join(msg_lines), bonus_exp
    
    def get_enlightenment_info(self, player: Player) -> str:
        """获取悟道信息"""
        trigger_chance = self._get_trigger_chance(player)
        cooldown_remaining = 0
        
        last_time = self._last_enlightenment.get(player.user_id, 0)
        if last_time > 0:
            elapsed = time.time() - last_time
            cooldown_remaining = max(0, ENLIGHTENMENT_CONFIG["cooldown"] - elapsed)
        
        info = (
            f"📖 悟道信息\n"
            f"━━━━━━━━━━━━━━━\n"
            f"当前悟道概率：{trigger_chance:.1%}\n"
            f"精神力：{player.mental_power:,}\n"
        )
        
        if cooldown_remaining > 0:
            minutes = int(cooldown_remaining // 60)
            info += f"冷却剩余：{minutes}分钟\n"
        else:
            info += f"状态：可触发悟道\n"
        
        info += (
            f"\n💡 提升精神力可增加悟道概率\n"
            f"💡 闭关修炼时有机会触发悟道"
        )
        
        return info
