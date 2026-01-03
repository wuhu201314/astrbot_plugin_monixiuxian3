# managers/gold_interaction_manager.py
"""灵石互动管理器 - 送/偷/抢灵石"""
import random
import time
from typing import Tuple, Dict
from ..data import DataBase
from ..models import Player

__all__ = ["GoldInteractionManager"]

# 配置
GOLD_INTERACTION_CONFIG = {
    # 赠送配置
    "gift": {
        "min_amount": 100,  # 最小赠送数量
    },
    # 偷窃配置
    "steal": {
        "cooldown": 3600,  # 冷却时间（秒）
        "base_success_rate": 0.4,  # 基础成功率40%
        "max_steal_ratio": 0.1,  # 最多偷取对方10%灵石
        "max_steal_amount": 5000,  # 单次最多偷5000
        "fail_penalty_ratio": 0.05,  # 失败惩罚：损失自己5%灵石
        "level_diff_bonus": 0.02,  # 每高1级增加2%成功率
    },
    # 抢夺配置
    "rob": {
        "cooldown": 7200,  # 冷却时间（秒）
        "base_success_rate": 0.5,  # 基础成功率50%
        "max_rob_ratio": 0.2,  # 最多抢夺对方20%灵石
        "max_rob_amount": 10000,  # 单次最多抢10000
        "fail_damage_ratio": 0.1,  # 失败惩罚：损失10%HP
        "fail_gold_loss_ratio": 0.1,  # 失败惩罚：损失10%灵石给对方
        "level_diff_bonus": 0.03,  # 每高1级增加3%成功率
    },
}


class GoldInteractionManager:
    """灵石互动管理器"""
    
    def __init__(self, db: DataBase, config_manager=None):
        self.db = db
        self.config_manager = config_manager
        self._steal_cooldowns: Dict[str, int] = {}  # {user_id: last_steal_time}
        self._rob_cooldowns: Dict[str, int] = {}  # {user_id: last_rob_time}
    
    async def gift_gold(self, sender: Player, receiver_id: str, amount: int) -> Tuple[bool, str]:
        """赠送灵石
        
        Args:
            sender: 发送者
            receiver_id: 接收者ID或道号
            amount: 数量
            
        Returns:
            (是否成功, 消息)
        """
        config = GOLD_INTERACTION_CONFIG["gift"]
        
        # 检查数量
        if amount < config["min_amount"]:
            return False, f"❌ 最少赠送 {config['min_amount']} 灵石！"
        
        if amount > sender.gold:
            return False, f"❌ 灵石不足！当前持有：{sender.gold:,}"
        
        # 检查接收者 - 先尝试ID，再尝试道号
        receiver = await self.db.get_player_by_id(receiver_id)
        if not receiver:
            receiver = await self.db.get_player_by_name(receiver_id)
        
        if not receiver:
            return False, "❌ 对方还未踏入修仙之路！"
        
        if receiver.user_id == sender.user_id:
            return False, "❌ 不能赠送给自己！"
        
        # 执行转账
        sender.gold -= amount
        receiver.gold += amount
        
        await self.db.update_player(sender)
        await self.db.update_player(receiver)
        
        receiver_name = receiver.user_name or f"道友{receiver.user_id[:6]}"
        sender_name = sender.user_name or f"道友{sender.user_id[:6]}"
        
        msg = (
            f"💝 赠送成功！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"赠送者：{sender_name}\n"
            f"接收者：{receiver_name}\n"
            f"数量：{amount:,} 灵石\n"
            f"━━━━━━━━━━━━━━━\n"
            f"你的灵石：{sender.gold:,}"
        )
        
        return True, msg
    
    async def steal_gold(self, thief: Player, target_id: str) -> Tuple[bool, str]:
        """偷窃灵石
        
        Args:
            thief: 偷窃者
            target_id: 目标ID或道号
            
        Returns:
            (是否成功, 消息)
        """
        config = GOLD_INTERACTION_CONFIG["steal"]
        
        # 检查冷却
        last_steal = self._steal_cooldowns.get(thief.user_id, 0)
        now = int(time.time())
        if now - last_steal < config["cooldown"]:
            remaining = config["cooldown"] - (now - last_steal)
            minutes = remaining // 60
            return False, f"❌ 偷窃冷却中！剩余 {minutes} 分钟"
        
        # 检查目标 - 先尝试ID，再尝试道号
        target = await self.db.get_player_by_id(target_id)
        if not target:
            target = await self.db.get_player_by_name(target_id)
        
        if not target:
            return False, "❌ 对方还未踏入修仙之路！"
        
        if target.user_id == thief.user_id:
            return False, "❌ 不能偷自己！"
        
        if target.gold < 100:
            return False, "❌ 对方太穷了，没什么可偷的..."
        
        # 计算成功率
        level_diff = thief.level_index - target.level_index
        success_rate = config["base_success_rate"] + level_diff * config["level_diff_bonus"]
        success_rate = max(0.1, min(0.8, success_rate))  # 限制在10%-80%
        
        # 记录冷却
        self._steal_cooldowns[thief.user_id] = now
        
        thief_name = thief.user_name or f"道友{thief.user_id[:6]}"
        target_name = target.user_name or f"道友{target_id[:6]}"
        
        # 判定结果
        if random.random() < success_rate:
            # 成功
            steal_amount = min(
                int(target.gold * config["max_steal_ratio"]),
                config["max_steal_amount"]
            )
            steal_amount = random.randint(steal_amount // 2, steal_amount)
            steal_amount = max(1, steal_amount)
            
            target.gold -= steal_amount
            thief.gold += steal_amount
            
            await self.db.update_player(thief)
            await self.db.update_player(target)
            
            msg = (
                f"🦊 偷窃成功！\n"
                f"━━━━━━━━━━━━━━━\n"
                f"你悄悄潜入 {target_name} 的洞府...\n"
                f"成功偷取 {steal_amount:,} 灵石！\n"
                f"━━━━━━━━━━━━━━━\n"
                f"你的灵石：{thief.gold:,}"
            )
        else:
            # 失败
            penalty = int(thief.gold * config["fail_penalty_ratio"])
            thief.gold = max(0, thief.gold - penalty)
            
            await self.db.update_player(thief)
            
            msg = (
                f"🚨 偷窃失败！\n"
                f"━━━━━━━━━━━━━━━\n"
                f"你潜入 {target_name} 的洞府时被发现！\n"
                f"慌忙逃跑中丢失了 {penalty:,} 灵石\n"
                f"━━━━━━━━━━━━━━━\n"
                f"你的灵石：{thief.gold:,}"
            )
        
        return True, msg
    
    async def rob_gold(self, robber: Player, target_id: str) -> Tuple[bool, str]:
        """抢夺灵石（需要战斗）
        
        Args:
            robber: 抢夺者
            target_id: 目标ID或道号
            
        Returns:
            (是否成功, 消息)
        """
        config = GOLD_INTERACTION_CONFIG["rob"]
        
        # 检查冷却
        last_rob = self._rob_cooldowns.get(robber.user_id, 0)
        now = int(time.time())
        if now - last_rob < config["cooldown"]:
            remaining = config["cooldown"] - (now - last_rob)
            minutes = remaining // 60
            return False, f"❌ 抢夺冷却中！剩余 {minutes} 分钟"
        
        # 检查目标 - 先尝试ID，再尝试道号
        target = await self.db.get_player_by_id(target_id)
        if not target:
            target = await self.db.get_player_by_name(target_id)
        
        if not target:
            return False, "❌ 对方还未踏入修仙之路！"
        
        if target.user_id == robber.user_id:
            return False, "❌ 不能抢自己！"
        
        if target.gold < 500:
            return False, "❌ 对方灵石太少，不值得出手..."
        
        # 计算成功率（基于境界差距和战力）
        level_diff = robber.level_index - target.level_index
        success_rate = config["base_success_rate"] + level_diff * config["level_diff_bonus"]
        
        # 战力影响
        robber_power = robber.physical_damage + robber.magic_damage + robber.physical_defense + robber.magic_defense
        target_power = target.physical_damage + target.magic_damage + target.physical_defense + target.magic_defense
        if target_power > 0:
            power_ratio = robber_power / target_power
            success_rate *= power_ratio
        
        success_rate = max(0.1, min(0.9, success_rate))  # 限制在10%-90%
        
        # 记录冷却
        self._rob_cooldowns[robber.user_id] = now
        
        robber_name = robber.user_name or f"道友{robber.user_id[:6]}"
        target_name = target.user_name or f"道友{target_id[:6]}"
        
        # 判定结果
        if random.random() < success_rate:
            # 成功
            rob_amount = min(
                int(target.gold * config["max_rob_ratio"]),
                config["max_rob_amount"]
            )
            rob_amount = random.randint(rob_amount // 2, rob_amount)
            rob_amount = max(1, rob_amount)
            
            target.gold -= rob_amount
            robber.gold += rob_amount
            
            await self.db.update_player(robber)
            await self.db.update_player(target)
            
            msg = (
                f"⚔️ 抢夺成功！\n"
                f"━━━━━━━━━━━━━━━\n"
                f"你向 {target_name} 发起挑战！\n"
                f"一番激战后，你获胜了！\n"
                f"抢得 {rob_amount:,} 灵石！\n"
                f"━━━━━━━━━━━━━━━\n"
                f"你的灵石：{robber.gold:,}"
            )
        else:
            # 失败 - 损失灵石给对方
            gold_loss = int(robber.gold * config["fail_gold_loss_ratio"])
            robber.gold = max(0, robber.gold - gold_loss)
            target.gold += gold_loss
            
            # HP损失
            hp_loss = int(robber.hp * config["fail_damage_ratio"]) if robber.hp > 0 else 0
            robber.hp = max(1, robber.hp - hp_loss)
            
            await self.db.update_player(robber)
            await self.db.update_player(target)
            
            msg = (
                f"💀 抢夺失败！\n"
                f"━━━━━━━━━━━━━━━\n"
                f"你向 {target_name} 发起挑战！\n"
                f"一番激战后，你落败了...\n"
                f"损失 {gold_loss:,} 灵石\n"
            )
            if hp_loss > 0:
                msg += f"受伤损失 {hp_loss:,} HP\n"
            msg += (
                f"━━━━━━━━━━━━━━━\n"
                f"你的灵石：{robber.gold:,}"
            )
        
        return True, msg
    
    def get_interaction_info(self) -> str:
        """获取灵石互动说明"""
        steal_config = GOLD_INTERACTION_CONFIG["steal"]
        rob_config = GOLD_INTERACTION_CONFIG["rob"]
        
        return (
            f"💰 灵石互动系统\n"
            f"━━━━━━━━━━━━━━━\n"
            f"\n"
            f"【赠送灵石】\n"
            f"  命令：/送灵石 @某人 数量\n"
            f"  最少赠送100灵石\n"
            f"\n"
            f"【偷窃灵石】\n"
            f"  命令：/偷灵石 @某人\n"
            f"  冷却：{steal_config['cooldown'] // 60}分钟\n"
            f"  成功率：约{steal_config['base_success_rate']:.0%}（受境界影响）\n"
            f"  成功：偷取对方最多{steal_config['max_steal_ratio']:.0%}灵石\n"
            f"  失败：损失自己{steal_config['fail_penalty_ratio']:.0%}灵石\n"
            f"\n"
            f"【抢夺灵石】\n"
            f"  命令：/抢灵石 @某人\n"
            f"  冷却：{rob_config['cooldown'] // 60}分钟\n"
            f"  成功率：约{rob_config['base_success_rate']:.0%}（受境界和战力影响）\n"
            f"  成功：抢夺对方最多{rob_config['max_rob_ratio']:.0%}灵石\n"
            f"  失败：损失{rob_config['fail_gold_loss_ratio']:.0%}灵石给对方"
        )
