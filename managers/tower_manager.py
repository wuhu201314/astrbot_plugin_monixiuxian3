# managers/tower_manager.py
"""通天塔系统管理器"""
import random
import time
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
from ..data import DataBase
from ..models import Player
from .combat_manager import CombatManager, CombatStats

__all__ = ["TowerManager"]


@dataclass
class TowerBoss:
    """通天塔Boss"""
    floor: int
    name: str
    hp: int
    max_hp: int
    atk: int
    defense: int = 0


class TowerManager:
    """通天塔管理器"""
    
    def __init__(self, db: DataBase, combat_mgr: CombatManager, config_manager=None):
        self.db = db
        self.combat_mgr = combat_mgr
        self.config = config_manager.tower_config if config_manager else {}
        
        # 配置
        self.base_hp_mult = self.config.get("base_hp_mult", 0.8)
        self.base_atk_mult = self.config.get("base_atk_mult", 0.6)
        self.hp_growth = self.config.get("hp_growth_per_floor", 0.05)
        self.atk_growth = self.config.get("atk_growth_per_floor", 0.03)
        self.points_per_floor = self.config.get("points_per_floor", 100)
        self.bonus_points = self.config.get("bonus_points_per_10_floors", 500)
        self.speed_run_floors = self.config.get("speed_run_floors", 10)
        self.boss_names = self.config.get("boss_names", ["塔灵", "守卫", "魔影"])
        self.floor_rewards = self.config.get("floor_rewards", {})
        self.shop_items = self.config.get("shop_items", [])
    
    def _generate_boss(self, floor: int, player_exp: int) -> TowerBoss:
        """根据层数和玩家修为生成Boss"""
        # 基础属性 = 玩家修为 * 基础倍率
        base_hp = int(player_exp * self.base_hp_mult)
        base_atk = int(player_exp * self.base_atk_mult / 10)
        
        # 层数成长
        floor_mult = 1 + (floor - 1) * self.hp_growth
        atk_mult = 1 + (floor - 1) * self.atk_growth
        
        hp = int(base_hp * floor_mult)
        atk = int(base_atk * atk_mult)
        
        # 每10层增加防御
        defense = (floor // 10) * 5
        
        # Boss名称
        name_index = (floor - 1) % len(self.boss_names)
        boss_name = f"第{floor}层·{self.boss_names[name_index]}"
        
        return TowerBoss(
            floor=floor,
            name=boss_name,
            hp=hp,
            max_hp=hp,
            atk=atk,
            defense=min(defense, 50)  # 最高50%减伤
        )
    
    async def get_player_tower_data(self, user_id: str) -> dict:
        """获取玩家通天塔数据"""
        data = await self.db.ext.get_tower_data(user_id)
        if not data:
            # 初始化数据
            data = {
                "current_floor": 0,
                "highest_floor": 0,
                "points": 0,
                "total_points": 0,
                "weekly_purchases": {}
            }
            await self.db.ext.save_tower_data(user_id, data)
        return data
    
    async def challenge_floor(self, player: Player) -> Tuple[bool, str, dict]:
        """挑战通天塔下一层
        
        Returns:
            (是否胜利, 消息, 结果数据)
        """
        tower_data = await self.get_player_tower_data(player.user_id)
        next_floor = tower_data["current_floor"] + 1
        
        # 生成Boss
        boss = self._generate_boss(next_floor, player.experience)
        
        # 获取玩家buff
        impart_info = await self.db.ext.get_impart_info(player.user_id)
        hp_buff = impart_info.impart_hp_per if impart_info else 0.0
        mp_buff = impart_info.impart_mp_per if impart_info else 0.0
        atk_buff = impart_info.impart_atk_per if impart_info else 0.0
        crit_buff = impart_info.impart_know_per if impart_info else 0.0
        
        # 计算玩家属性
        if player.hp == 0:
            hp, mp = self.combat_mgr.calculate_hp_mp(player.experience, hp_buff, mp_buff)
            atk = self.combat_mgr.calculate_atk(player.experience, player.atkpractice, atk_buff)
            player.hp = hp
            player.mp = mp
            player.atk = atk
        
        player_stats = CombatStats(
            user_id=player.user_id,
            name=player.user_name or f"道友{player.user_id[:6]}",
            hp=player.hp,
            max_hp=int(player.experience * (1 + hp_buff) // 2),
            mp=player.mp,
            max_mp=int(player.experience * (1 + mp_buff)),
            atk=player.atk,
            defense=0,
            crit_rate=int(crit_buff * 100),
            exp=player.experience
        )
        
        boss_stats = CombatStats(
            user_id=f"tower_boss_{next_floor}",
            name=boss.name,
            hp=boss.hp,
            max_hp=boss.max_hp,
            mp=boss.max_hp,
            max_mp=boss.max_hp,
            atk=boss.atk,
            defense=boss.defense,
            crit_rate=20 + next_floor // 10,  # 层数越高会心越高
            exp=0
        )
        
        # 战斗
        result = self.combat_mgr.player_vs_boss(player_stats, boss_stats)
        
        # 处理结果
        victory = result["winner"] == player.user_id
        rewards = {"points": 0, "gold": 0, "exp": 0}
        
        if victory:
            # 更新层数
            tower_data["current_floor"] = next_floor
            if next_floor > tower_data["highest_floor"]:
                tower_data["highest_floor"] = next_floor
            
            # 积分奖励
            points_earned = self.points_per_floor
            if next_floor % 10 == 0:
                points_earned += self.bonus_points
            
            tower_data["points"] += points_earned
            tower_data["total_points"] += points_earned
            rewards["points"] = points_earned
            
            # 每10层额外奖励
            floor_key = str(next_floor)
            if floor_key in self.floor_rewards:
                floor_reward = self.floor_rewards[floor_key]
                rewards["gold"] = floor_reward.get("gold", 0)
                rewards["exp"] = floor_reward.get("exp", 0)
                player.gold += rewards["gold"]
                player.experience += rewards["exp"]
            
            await self.db.ext.save_tower_data(player.user_id, tower_data)
            
            # 更新玩家HP
            player.hp = result["player_final_hp"]
            await self.db.update_player(player)
            
            msg = f"""
🗼 通天塔 - 第{next_floor}层
━━━━━━━━━━━━━━━
✅ 挑战成功！

战斗回合：{result['rounds']}
剩余气血：{result['player_final_hp']:,}

📊 获得奖励：
  · 积分 +{points_earned}
"""
            if rewards["gold"] > 0:
                msg += f"  · 灵石 +{rewards['gold']:,}\n"
            if rewards["exp"] > 0:
                msg += f"  · 修为 +{rewards['exp']:,}\n"
            
            msg += f"""
━━━━━━━━━━━━━━━
当前层数：{next_floor} | 积分：{tower_data['points']:,}
            """.strip()
        else:
            # 失败不扣层数
            player.hp = max(1, result["player_final_hp"])
            await self.db.update_player(player)
            
            msg = f"""
🗼 通天塔 - 第{next_floor}层
━━━━━━━━━━━━━━━
❌ 挑战失败！

{boss.name} 太强了！
战斗回合：{result['rounds']}

💡 提示：提升修为后再来挑战
当前层数：{tower_data['current_floor']} | 积分：{tower_data['points']:,}
            """.strip()
        
        return victory, msg, {"victory": victory, "floor": next_floor, "rewards": rewards}
    
    async def speed_run(self, player: Player, floors: int = 10) -> Tuple[bool, str, dict]:
        """速通通天塔（连续挑战多层）"""
        floors = min(max(1, floors), self.speed_run_floors)
        
        results = []
        total_points = 0
        total_gold = 0
        total_exp = 0
        victories = 0
        
        for i in range(floors):
            victory, _, result_data = await self.challenge_floor(player)
            results.append(result_data)
            
            if victory:
                victories += 1
                total_points += result_data["rewards"]["points"]
                total_gold += result_data["rewards"]["gold"]
                total_exp += result_data["rewards"]["exp"]
                # 刷新玩家数据
                player = await self.db.get_player_by_id(player.user_id)
            else:
                break
        
        tower_data = await self.get_player_tower_data(player.user_id)
        
        msg = f"""
🗼 通天塔速通结果
━━━━━━━━━━━━━━━
挑战层数：{victories}/{floors}
当前层数：{tower_data['current_floor']}

📊 总计获得：
  · 积分 +{total_points:,}
  · 灵石 +{total_gold:,}
  · 修为 +{total_exp:,}

当前积分：{tower_data['points']:,}
        """.strip()
        
        return victories == floors, msg, {
            "victories": victories,
            "total_points": total_points,
            "total_gold": total_gold,
            "total_exp": total_exp
        }
    
    async def get_tower_info(self, user_id: str) -> str:
        """获取通天塔信息"""
        tower_data = await self.get_player_tower_data(user_id)
        
        return f"""
🗼 通天塔信息
━━━━━━━━━━━━━━━
当前层数：{tower_data['current_floor']}
最高记录：{tower_data['highest_floor']}
当前积分：{tower_data['points']:,}
累计积分：{tower_data['total_points']:,}
━━━━━━━━━━━━━━━
💡 每周一0点重置层数
💡 积分可在通天塔商店兑换
        """.strip()
    
    async def get_next_boss_info(self, player: Player) -> str:
        """获取下一层Boss信息"""
        tower_data = await self.get_player_tower_data(player.user_id)
        next_floor = tower_data["current_floor"] + 1
        
        boss = self._generate_boss(next_floor, player.experience)
        
        # 下一个10层奖励
        next_milestone = ((next_floor - 1) // 10 + 1) * 10
        milestone_reward = self.floor_rewards.get(str(next_milestone), {})
        
        msg = f"""
🗼 通天塔 - 第{next_floor}层Boss
━━━━━━━━━━━━━━━
👹 {boss.name}
HP：{boss.hp:,}
ATK：{boss.atk:,}
防御：{boss.defense}%减伤
━━━━━━━━━━━━━━━
📊 通关奖励：
  · 积分 +{self.points_per_floor}
"""
        if next_floor % 10 == 0:
            msg += f"  · 额外积分 +{self.bonus_points}\n"
        if milestone_reward:
            msg += f"\n🎁 第{next_milestone}层里程碑奖励：\n"
            if milestone_reward.get("gold"):
                msg += f"  · 灵石 +{milestone_reward['gold']:,}\n"
            if milestone_reward.get("exp"):
                msg += f"  · 修为 +{milestone_reward['exp']:,}\n"
        
        return msg.strip()
    
    async def get_floor_ranking(self, limit: int = 10) -> str:
        """获取通天塔层数排行榜"""
        rankings = await self.db.ext.get_tower_floor_ranking(limit)
        
        if not rankings:
            return "❌ 暂无排行数据"
        
        msg = "🗼 通天塔排行榜\n━━━━━━━━━━━━━━━\n"
        
        for i, (user_id, name, floor) in enumerate(rankings, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            display_name = name or f"道友{user_id[:6]}"
            msg += f"{medal} {display_name} - 第{floor}层\n"
        
        return msg.strip()
    
    async def get_points_ranking(self, limit: int = 10) -> str:
        """获取通天塔积分排行榜"""
        rankings = await self.db.ext.get_tower_points_ranking(limit)
        
        if not rankings:
            return "❌ 暂无排行数据"
        
        msg = "🗼 通天塔积分排行榜\n━━━━━━━━━━━━━━━\n"
        
        for i, (user_id, name, points) in enumerate(rankings, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            display_name = name or f"道友{user_id[:6]}"
            msg += f"{medal} {display_name} - {points:,}积分\n"
        
        return msg.strip()
    
    def get_shop_info(self) -> str:
        """获取商店信息"""
        msg = "🗼 通天塔商店\n━━━━━━━━━━━━━━━\n"
        
        for item in self.shop_items:
            msg += f"\n[{item['id']}] {item['name']}\n"
            msg += f"    💰 {item['cost']:,}积分 | 限购{item['limit']}次/周\n"
            msg += f"    📝 {item['desc']}\n"
        
        msg += "\n━━━━━━━━━━━━━━━\n"
        msg += "💡 使用「通天塔兑换 编号」购买"
        
        return msg
    
    async def exchange_item(self, player: Player, item_id: int) -> Tuple[bool, str]:
        """兑换商店物品"""
        # 查找物品
        item = None
        for shop_item in self.shop_items:
            if shop_item["id"] == item_id:
                item = shop_item
                break
        
        if not item:
            return False, "❌ 未找到该商品！"
        
        tower_data = await self.get_player_tower_data(player.user_id)
        
        # 检查积分
        if tower_data["points"] < item["cost"]:
            return False, f"❌ 积分不足！需要 {item['cost']:,}，当前 {tower_data['points']:,}"
        
        # 检查限购
        purchases = tower_data.get("weekly_purchases", {})
        item_key = str(item_id)
        current_purchases = purchases.get(item_key, 0)
        
        if current_purchases >= item["limit"]:
            return False, f"❌ 本周已达购买上限（{item['limit']}次）！"
        
        # 扣除积分
        tower_data["points"] -= item["cost"]
        purchases[item_key] = current_purchases + 1
        tower_data["weekly_purchases"] = purchases
        await self.db.ext.save_tower_data(player.user_id, tower_data)
        
        # 应用效果
        effect = item["effect"]
        value = item["value"]
        effect_msg = ""
        
        if effect == "exp":
            player.experience += value
            effect_msg = f"获得 {value:,} 修为"
        elif effect == "gold":
            player.gold += value
            effect_msg = f"获得 {value:,} 灵石"
        elif effect == "heal":
            # 恢复气血
            impart_info = await self.db.ext.get_impart_info(player.user_id)
            hp_buff = impart_info.impart_hp_per if impart_info else 0.0
            max_hp = int(player.experience * (1 + hp_buff) // 2)
            player.hp = max_hp
            effect_msg = f"气血恢复至 {max_hp:,}"
        elif effect == "atk_permanent":
            player.atkpractice += value // 10  # 转换为攻击修炼等级
            effect_msg = f"永久攻击力提升"
        elif effect == "breakthrough_rate":
            # 存储到额外数据中
            extra = tower_data.get("extra_buffs", {})
            extra["breakthrough_rate"] = extra.get("breakthrough_rate", 0) + value
            tower_data["extra_buffs"] = extra
            await self.db.ext.save_tower_data(player.user_id, tower_data)
            effect_msg = f"下次突破成功率 +{value}%"
        
        await self.db.update_player(player)
        
        return True, f"""
✅ 兑换成功！
━━━━━━━━━━━━━━━
物品：{item['name']}
效果：{effect_msg}
剩余积分：{tower_data['points']:,}
本周已购：{purchases[item_key]}/{item['limit']}
        """.strip()
    
    async def weekly_reset(self):
        """每周重置（由定时任务调用）"""
        await self.db.ext.reset_tower_weekly()
