# managers/social_manager.py
"""社交互动系统管理器 - 拜师收徒、道侣、论道"""
import random
import time
from typing import Tuple, Optional, Dict, List
from ..data import DataBase
from ..models import Player

__all__ = ["SocialManager"]


# 配置
SOCIAL_CONFIG = {
    # 拜师系统
    "master_min_level_diff": 5,  # 师父至少比徒弟高5级
    "master_max_disciples": 3,  # 最多收3个徒弟
    "disciple_exp_bonus": 0.1,  # 徒弟修炼加成10%
    "master_exp_share": 0.05,  # 师父获得徒弟修为5%
    
    # 道侣系统
    "couple_exp_bonus": 0.15,  # 道侣修炼加成15%
    "couple_cultivation_bonus": 1.2,  # 双修加成1.2倍
    "proposal_cost": 5000,  # 求道侣花费5000灵石
    
    # 论道系统
    "debate_cooldown": 3600,  # 论道冷却1小时
    "debate_exp_base": 500,  # 基础修为奖励
    "debate_exp_mult": 0.01,  # 修为奖励倍率
    "debate_gold_base": 100,  # 基础灵石奖励
}


class SocialManager:
    """社交互动管理器"""
    
    def __init__(self, db: DataBase, config_manager=None):
        self.db = db
        self.config = SOCIAL_CONFIG
        # 临时存储请求 {target_id: {type, from_id, from_name, time}}
        self._pending_requests: Dict[str, dict] = {}
    
    # ========== 拜师收徒系统 ==========
    
    async def request_apprentice(self, master: Player, disciple_id: str) -> Tuple[bool, str]:
        """师父发起收徒请求"""
        # 先尝试ID，再尝试道号
        disciple = await self.db.get_player_by_id(disciple_id)
        if not disciple:
            disciple = await self.db.get_player_by_name(disciple_id)
        
        if not disciple:
            return False, "❌ 对方还未踏入修仙之路！"
        
        disciple_id = disciple.user_id  # 确保使用正确的ID
        
        if master.user_id == disciple_id:
            return False, "❌ 不能收自己为徒！"
        
        # 检查等级差距
        min_diff = self.config["master_min_level_diff"]
        if master.level_index - disciple.level_index < min_diff:
            return False, f"❌ 你的境界至少要比对方高{min_diff}级才能收徒！"
        
        # 检查师父是否已有师父（不能既是徒弟又收徒）
        master_data = await self.db.ext.get_social_data(master.user_id)
        if master_data and master_data.get("master_id"):
            return False, "❌ 你已有师父，不能再收徒！"
        
        # 检查徒弟数量
        disciples = await self.db.ext.get_disciples(master.user_id)
        if len(disciples) >= self.config["master_max_disciples"]:
            return False, f"❌ 你已有{len(disciples)}个徒弟，无法再收徒！"
        
        # 检查对方是否已有师父
        disciple_data = await self.db.ext.get_social_data(disciple_id)
        if disciple_data and disciple_data.get("master_id"):
            return False, "❌ 对方已有师父！"
        
        # 发起请求
        master_name = master.user_name or f"道友{master.user_id[:6]}"
        self._pending_requests[disciple_id] = {
            "type": "apprentice",
            "from_id": master.user_id,
            "from_name": master_name,
            "time": int(time.time())
        }
        
        disciple_name = disciple.user_name or f"道友{disciple_id[:6]}"
        return True, f"✅ 已向【{disciple_name}】发出收徒请求！\n对方发送「拜师」即可成为你的徒弟。"
    
    async def request_master(self, disciple: Player, master_id: str) -> Tuple[bool, str]:
        """徒弟发起拜师请求"""
        # 先尝试ID，再尝试道号
        master = await self.db.get_player_by_id(master_id)
        if not master:
            master = await self.db.get_player_by_name(master_id)
        
        if not master:
            return False, "❌ 对方还未踏入修仙之路！"
        
        master_id = master.user_id  # 确保使用正确的ID
        
        if disciple.user_id == master_id:
            return False, "❌ 不能拜自己为师！"
        
        # 检查等级差距
        min_diff = self.config["master_min_level_diff"]
        if master.level_index - disciple.level_index < min_diff:
            return False, f"❌ 对方境界至少要比你高{min_diff}级才能拜师！"
        
        # 检查自己是否已有师父
        disciple_data = await self.db.ext.get_social_data(disciple.user_id)
        if disciple_data and disciple_data.get("master_id"):
            return False, "❌ 你已有师父！"
        
        # 检查对方徒弟数量
        disciples = await self.db.ext.get_disciples(master_id)
        if len(disciples) >= self.config["master_max_disciples"]:
            return False, f"❌ 对方徒弟已满！"
        
        # 发起请求
        disciple_name = disciple.user_name or f"道友{disciple.user_id[:6]}"
        self._pending_requests[master_id] = {
            "type": "master",
            "from_id": disciple.user_id,
            "from_name": disciple_name,
            "time": int(time.time())
        }
        
        master_name = master.user_name or f"道友{master_id[:6]}"
        return True, f"✅ 已向【{master_name}】发出拜师请求！\n对方发送「收徒」即可收你为徒。"
    
    async def accept_apprentice(self, user_id: str) -> Tuple[bool, str]:
        """接受拜师/收徒请求"""
        request = self._pending_requests.get(user_id)
        if not request:
            return False, "❌ 没有待处理的师徒请求！"
        
        # 检查请求是否过期（5分钟）
        if int(time.time()) - request["time"] > 300:
            del self._pending_requests[user_id]
            return False, "❌ 请求已过期！"
        
        from_id = request["from_id"]
        from_name = request["from_name"]
        req_type = request["type"]
        
        # 确定师徒关系
        if req_type == "apprentice":
            # 对方要收我为徒
            master_id = from_id
            disciple_id = user_id
        else:
            # 对方要拜我为师
            master_id = user_id
            disciple_id = from_id
        
        # 建立师徒关系
        await self.db.ext.set_master_disciple(master_id, disciple_id)
        
        del self._pending_requests[user_id]
        
        master = await self.db.get_player_by_id(master_id)
        disciple = await self.db.get_player_by_id(disciple_id)
        master_name = master.user_name if master else f"道友{master_id[:6]}"
        disciple_name = disciple.user_name if disciple else f"道友{disciple_id[:6]}"
        
        return True, f"""
🎊 师徒关系建立！
━━━━━━━━━━━━━━━
👨‍🏫 师父：{master_name}
👨‍🎓 徒弟：{disciple_name}
━━━━━━━━━━━━━━━
📈 徒弟修炼获得 +{int(self.config['disciple_exp_bonus']*100)}% 加成
📈 师父获得徒弟修为的 {int(self.config['master_exp_share']*100)}%
        """.strip()
    
    async def leave_master(self, disciple: Player) -> Tuple[bool, str]:
        """离开师门"""
        social_data = await self.db.ext.get_social_data(disciple.user_id)
        if not social_data or not social_data.get("master_id"):
            return False, "❌ 你没有师父！"
        
        master_id = social_data["master_id"]
        master = await self.db.get_player_by_id(master_id)
        master_name = master.user_name if master else f"道友{master_id[:6]}"
        
        await self.db.ext.remove_master_disciple(disciple.user_id)
        
        return True, f"💔 你已离开【{master_name}】的师门。"
    
    async def get_master_info(self, user_id: str) -> str:
        """获取师徒信息"""
        social_data = await self.db.ext.get_social_data(user_id)
        player = await self.db.get_player_by_id(user_id)
        
        msg = "👨‍👩‍👧‍👦 师徒信息\n━━━━━━━━━━━━━━━\n"
        
        # 师父信息
        if social_data and social_data.get("master_id"):
            master = await self.db.get_player_by_id(social_data["master_id"])
            master_name = master.user_name if master else "未知"
            msg += f"👨‍🏫 师父：{master_name}\n"
            msg += f"   修炼加成：+{int(self.config['disciple_exp_bonus']*100)}%\n"
        else:
            msg += "👨‍🏫 师父：无\n"
        
        # 徒弟信息
        disciples = await self.db.ext.get_disciples(user_id)
        if disciples:
            msg += f"\n👨‍🎓 徒弟（{len(disciples)}/{self.config['master_max_disciples']}）：\n"
            for d_id in disciples:
                d = await self.db.get_player_by_id(d_id)
                d_name = d.user_name if d else f"道友{d_id[:6]}"
                msg += f"   · {d_name}\n"
            msg += f"   收益：徒弟修为的 {int(self.config['master_exp_share']*100)}%\n"
        else:
            msg += f"\n👨‍🎓 徒弟：无（最多{self.config['master_max_disciples']}人）\n"
        
        msg += "\n━━━━━━━━━━━━━━━\n"
        msg += "💡 收徒 @某人 / 拜师 @某人"
        
        return msg
    
    # ========== 道侣系统 ==========
    
    async def propose(self, player: Player, target_id: str) -> Tuple[bool, str]:
        """求道侣"""
        # 先尝试ID，再尝试道号
        target = await self.db.get_player_by_id(target_id)
        if not target:
            target = await self.db.get_player_by_name(target_id)
        
        if not target:
            return False, "❌ 对方还未踏入修仙之路！"
        
        target_id = target.user_id  # 确保使用正确的ID
        
        if player.user_id == target_id:
            return False, "❌ 不能和自己结为道侣！"
        
        # 检查灵石
        cost = self.config["proposal_cost"]
        if player.gold < cost:
            return False, f"❌ 灵石不足！求道侣需要 {cost:,} 灵石。"
        
        # 检查双方是否已有道侣
        player_data = await self.db.ext.get_social_data(player.user_id)
        if player_data and player_data.get("couple_id"):
            return False, "❌ 你已有道侣！"
        
        target_data = await self.db.ext.get_social_data(target_id)
        if target_data and target_data.get("couple_id"):
            return False, "❌ 对方已有道侣！"
        
        # 扣除灵石
        player.gold -= cost
        await self.db.update_player(player)
        
        # 发起请求
        player_name = player.user_name or f"道友{player.user_id[:6]}"
        self._pending_requests[target_id] = {
            "type": "couple",
            "from_id": player.user_id,
            "from_name": player_name,
            "time": int(time.time())
        }
        
        target_name = target.user_name or f"道友{target_id[:6]}"
        return True, f"""
💕 求道侣
━━━━━━━━━━━━━━━
你向【{target_name}】送出了定情信物！
花费：{cost:,} 灵石

等待对方回应...
对方发送「接受道侣」即可结为道侣。
        """.strip()
    
    async def accept_couple(self, user_id: str) -> Tuple[bool, str]:
        """接受道侣请求"""
        request = self._pending_requests.get(user_id)
        if not request or request["type"] != "couple":
            return False, "❌ 没有待处理的道侣请求！"
        
        if int(time.time()) - request["time"] > 300:
            del self._pending_requests[user_id]
            return False, "❌ 请求已过期！"
        
        from_id = request["from_id"]
        from_name = request["from_name"]
        
        # 建立道侣关系
        await self.db.ext.set_couple(from_id, user_id)
        
        del self._pending_requests[user_id]
        
        user = await self.db.get_player_by_id(user_id)
        user_name = user.user_name if user else f"道友{user_id[:6]}"
        
        return True, f"""
💕 喜结道侣！
━━━━━━━━━━━━━━━
🎊 {from_name} ❤️ {user_name}
从此携手共修仙道！
━━━━━━━━━━━━━━━
📈 双方修炼获得 +{int(self.config['couple_exp_bonus']*100)}% 加成
📈 双修效果 x{self.config['couple_cultivation_bonus']}
        """.strip()
    
    async def reject_couple(self, user_id: str) -> Tuple[bool, str]:
        """拒绝道侣请求"""
        request = self._pending_requests.get(user_id)
        if not request or request["type"] != "couple":
            return False, "❌ 没有待处理的道侣请求！"
        
        from_name = request["from_name"]
        del self._pending_requests[user_id]
        
        return True, f"💔 你拒绝了【{from_name}】的道侣请求。"
    
    async def divorce(self, player: Player) -> Tuple[bool, str]:
        """解除道侣"""
        social_data = await self.db.ext.get_social_data(player.user_id)
        if not social_data or not social_data.get("couple_id"):
            return False, "❌ 你没有道侣！"
        
        couple_id = social_data["couple_id"]
        couple = await self.db.get_player_by_id(couple_id)
        couple_name = couple.user_name if couple else f"道友{couple_id[:6]}"
        
        await self.db.ext.remove_couple(player.user_id)
        
        return True, f"💔 你与【{couple_name}】解除了道侣关系。"
    
    async def get_couple_info(self, user_id: str) -> str:
        """获取道侣信息"""
        social_data = await self.db.ext.get_social_data(user_id)
        
        if not social_data or not social_data.get("couple_id"):
            return f"""
💕 道侣信息
━━━━━━━━━━━━━━━
当前状态：单身
━━━━━━━━━━━━━━━
💡 求道侣 @某人（花费{self.config['proposal_cost']:,}灵石）
            """.strip()
        
        couple = await self.db.get_player_by_id(social_data["couple_id"])
        couple_name = couple.user_name if couple else "未知"
        
        return f"""
💕 道侣信息
━━━━━━━━━━━━━━━
道侣：{couple_name}
━━━━━━━━━━━━━━━
📈 修炼加成：+{int(self.config['couple_exp_bonus']*100)}%
📈 双修加成：x{self.config['couple_cultivation_bonus']}
━━━━━━━━━━━━━━━
💡 解除道侣 - 分手
        """.strip()
    
    # ========== 论道系统 ==========
    
    async def debate(self, player: Player, target_id: str) -> Tuple[bool, str]:
        """论道"""
        # 先尝试ID，再尝试道号
        target = await self.db.get_player_by_id(target_id)
        if not target:
            target = await self.db.get_player_by_name(target_id)
        
        if not target:
            return False, "❌ 对方还未踏入修仙之路！"
        
        target_id = target.user_id  # 确保使用正确的ID
        
        if player.user_id == target_id:
            return False, "❌ 不能和自己论道！"
        
        # 检查冷却
        last_debate = await self.db.ext.get_debate_cooldown(player.user_id, target_id)
        if last_debate:
            remaining = self.config["debate_cooldown"] - (int(time.time()) - last_debate)
            if remaining > 0:
                return False, f"❌ 论道冷却中，还需 {remaining // 60} 分钟。"
        
        # 论道结果
        player_name = player.user_name or f"道友{player.user_id[:6]}"
        target_name = target.user_name or f"道友{target_id[:6]}"
        
        # 根据双方修为计算胜率
        total_exp = player.experience + target.experience
        player_win_rate = player.experience / total_exp if total_exp > 0 else 0.5
        
        # 加入随机因素
        player_win_rate = player_win_rate * 0.7 + random.random() * 0.3
        
        winner = player if random.random() < player_win_rate else target
        loser = target if winner == player else player
        
        # 计算奖励
        base_exp = self.config["debate_exp_base"]
        exp_mult = self.config["debate_exp_mult"]
        gold_base = self.config["debate_gold_base"]
        
        # 胜者获得更多
        winner_exp = int(base_exp + loser.experience * exp_mult)
        loser_exp = int(base_exp * 0.5 + winner.experience * exp_mult * 0.3)
        winner_gold = gold_base
        
        # 发放奖励
        winner.experience += winner_exp
        winner.gold += winner_gold
        loser.experience += loser_exp
        
        await self.db.update_player(winner)
        await self.db.update_player(loser)
        
        # 记录冷却
        await self.db.ext.set_debate_cooldown(player.user_id, target_id)
        
        winner_name = winner.user_name or f"道友{winner.user_id[:6]}"
        loser_name = loser.user_name or f"道友{loser.user_id[:6]}"
        
        # 论道话题
        topics = [
            "天道轮回", "阴阳五行", "长生之道", "剑道真意",
            "丹道精髓", "符箓奥秘", "阵法玄机", "炼器之法"
        ]
        topic = random.choice(topics)
        
        return True, f"""
📜 论道 - {topic}
━━━━━━━━━━━━━━━
{player_name} VS {target_name}

🏆 胜者：{winner_name}
   获得：{winner_exp:,} 修为 + {winner_gold} 灵石

📖 败者：{loser_name}
   获得：{loser_exp:,} 修为（有所领悟）

━━━━━━━━━━━━━━━
💡 论道使双方都有所收获！
        """.strip()
    
    # ========== 加成计算 ==========
    
    async def get_cultivation_bonus(self, user_id: str) -> float:
        """获取修炼加成（师徒+道侣）"""
        bonus = 0.0
        social_data = await self.db.ext.get_social_data(user_id)
        
        if social_data:
            # 徒弟加成
            if social_data.get("master_id"):
                bonus += self.config["disciple_exp_bonus"]
            
            # 道侣加成
            if social_data.get("couple_id"):
                bonus += self.config["couple_exp_bonus"]
        
        return bonus
    
    async def distribute_master_exp(self, disciple_id: str, exp_gained: int):
        """分配师父收益"""
        social_data = await self.db.ext.get_social_data(disciple_id)
        if not social_data or not social_data.get("master_id"):
            return
        
        master_id = social_data["master_id"]
        master = await self.db.get_player_by_id(master_id)
        if master:
            master_exp = int(exp_gained * self.config["master_exp_share"])
            if master_exp > 0:
                master.experience += master_exp
                await self.db.update_player(master)
