# managers/bounty_manager.py
"""悬赏令系统管理器"""
import time
import random
import json
from typing import Tuple, List, Optional, Dict, TYPE_CHECKING
from ..data import DataBase
from ..models import Player

if TYPE_CHECKING:
    from ..core import StorageRingManager

__all__ = ["BountyManager"]

# 悬赏任务配置
BOUNTY_TEMPLATES = [
    {"id": 1, "name": "击杀妖兽", "type": "kill", "min_count": 3, "max_count": 10, "base_reward": 500, "cooldown": 3600},
    {"id": 2, "name": "采集灵草", "type": "gather", "min_count": 5, "max_count": 15, "base_reward": 300, "cooldown": 1800},
    {"id": 3, "name": "护送商队", "type": "escort", "min_count": 1, "max_count": 3, "base_reward": 800, "cooldown": 7200},
    {"id": 4, "name": "探索遗迹", "type": "explore", "min_count": 2, "max_count": 5, "base_reward": 600, "cooldown": 5400},
    {"id": 5, "name": "收集灵石", "type": "collect", "min_count": 1000, "max_count": 5000, "base_reward": 200, "cooldown": 900},
]

# 悬赏物品奖励表
BOUNTY_ITEM_REWARDS = {
    "kill": [
        {"name": "灵兽毛皮", "weight": 40, "min": 1, "max": 3},
        {"name": "妖兽精血", "weight": 30, "min": 1, "max": 2},
        {"name": "灵兽内丹", "weight": 20, "min": 1, "max": 1},
        {"name": "玄铁", "weight": 10, "min": 1, "max": 2},
    ],
    "gather": [
        {"name": "灵草", "weight": 50, "min": 2, "max": 5},
        {"name": "精铁", "weight": 30, "min": 1, "max": 3},
        {"name": "灵石碎片", "weight": 20, "min": 3, "max": 8},
    ],
    "escort": [
        {"name": "玄铁", "weight": 35, "min": 2, "max": 4},
        {"name": "星辰石", "weight": 25, "min": 1, "max": 2},
        {"name": "功法残页", "weight": 25, "min": 1, "max": 1},
        {"name": "天材地宝", "weight": 15, "min": 1, "max": 1},
    ],
    "explore": [
        {"name": "灵草", "weight": 30, "min": 2, "max": 4},
        {"name": "玄铁", "weight": 25, "min": 1, "max": 3},
        {"name": "功法残页", "weight": 25, "min": 1, "max": 1},
        {"name": "秘境精华", "weight": 20, "min": 1, "max": 2},
    ],
    "collect": [
        {"name": "灵石碎片", "weight": 50, "min": 5, "max": 10},
        {"name": "精铁", "weight": 30, "min": 2, "max": 4},
        {"name": "灵草", "weight": 20, "min": 1, "max": 3},
    ],
}

class BountyManager:
    """悬赏令管理器"""
    
    BOUNTY_CACHE_DURATION = 600  # 任务列表缓存10分钟
    
    def __init__(self, db: DataBase, storage_ring_manager: Optional["StorageRingManager"] = None):
        self.db = db
        self.storage_ring_manager = storage_ring_manager
        self._bounty_cache: Dict[str, Dict] = {}  # {user_id: {"bounties": [...], "expire_time": int}}
    
    def _get_cached_bounties(self, user_id: str) -> Optional[List[dict]]:
        """获取缓存的任务列表"""
        cache = self._bounty_cache.get(user_id)
        if cache and cache["expire_time"] > int(time.time()):
            return cache["bounties"]
        return None
    
    def _set_cached_bounties(self, user_id: str, bounties: List[dict]):
        """缓存任务列表"""
        self._bounty_cache[user_id] = {
            "bounties": bounties,
            "expire_time": int(time.time()) + self.BOUNTY_CACHE_DURATION
        }
    
    async def get_bounty_list(self, player: Player) -> List[dict]:
        """获取可接取的悬赏任务列表（带缓存）"""
        # 检查缓存
        cached = self._get_cached_bounties(player.user_id)
        if cached:
            return cached
        
        # 根据玩家境界生成不同难度的任务
        level_multiplier = 1 + (player.level_index // 5) * 0.5
        
        bounties = []
        for template in BOUNTY_TEMPLATES:
            count = random.randint(template["min_count"], template["max_count"])
            reward = int(template["base_reward"] * level_multiplier * (count / template["min_count"]))
            
            bounties.append({
                "id": template["id"],
                "name": template["name"],
                "type": template["type"],
                "count": count,
                "reward": reward,
                "cooldown": template["cooldown"]
            })
        
        # 缓存任务列表
        self._set_cached_bounties(player.user_id, bounties)
        return bounties
    
    async def accept_bounty(self, player: Player, bounty_id: int) -> Tuple[bool, str]:
        """接取悬赏任务（使用缓存的任务数据，事务保护防止并发）"""
        # 获取任务模板（在事务外进行，减少锁持有时间）
        template = next((t for t in BOUNTY_TEMPLATES if t["id"] == bounty_id), None)
        if not template:
            return False, "无效的悬赏编号。"
        
        # 从缓存获取任务数据
        cached_bounties = self._get_cached_bounties(player.user_id)
        cached_bounty = None
        if cached_bounties:
            cached_bounty = next((b for b in cached_bounties if b["id"] == bounty_id), None)
        
        if cached_bounty:
            count = cached_bounty["count"]
            reward = cached_bounty["reward"]
        else:
            level_multiplier = 1 + (player.level_index // 5) * 0.5
            count = random.randint(template["min_count"], template["max_count"])
            reward = int(template["base_reward"] * level_multiplier * (count / template["min_count"]))
        
        # 使用事务保护，防止并发重复接取
        await self.db.conn.execute("BEGIN IMMEDIATE")
        try:
            # 事务内再次检查是否已有进行中的任务
            active = await self.db.ext.get_active_bounty(player.user_id)
            if active:
                await self.db.conn.rollback()
                return False, f"你已有进行中的悬赏：{active['bounty_name']}，请先完成或放弃。"
            
            # 检查放弃冷却
            cd_key = f"bounty_abandon_cd_{player.user_id}"
            cd_value = await self.db.ext.get_system_config(cd_key)
            if cd_value:
                cd_time = int(cd_value)
                now = int(time.time())
                if now < cd_time:
                    await self.db.conn.rollback()
                    remaining = (cd_time - now) // 60
                    return False, f"你刚放弃了悬赏任务，还需等待 {remaining} 分钟才能接取新任务。"
            
            expire_time = int(time.time()) + template["cooldown"]
            rewards_json = json.dumps({"stone": reward, "exp": reward * 10})
            
            # 直接在事务内插入，不调用会自动commit的方法
            await self.db.conn.execute(
                """
                INSERT INTO bounty_tasks (
                    user_id, bounty_id, bounty_name, target_type, 
                    target_count, current_progress, rewards, 
                    start_time, expire_time, status
                ) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, 1)
                """,
                (player.user_id, bounty_id, template["name"], template["type"], 
                 count, rewards_json, int(time.time()), expire_time)
            )
            await self.db.conn.commit()
            
            return True, (
                f"🎯 接取悬赏成功！\n"
                f"任务：{template['name']}\n"
                f"目标：完成 {count} 次\n"
                f"奖励：{reward:,} 灵石 + {reward * 10:,} 修为\n"
                f"时限：{template['cooldown'] // 60} 分钟"
            )
        except Exception:
            await self.db.conn.rollback()
            raise
    
    async def check_bounty_status(self, player: Player) -> Tuple[bool, str]:
        """查看悬赏任务状态"""
        active = await self.db.ext.get_active_bounty(player.user_id)
        if not active:
            return False, "你当前没有进行中的悬赏任务。\n使用 /悬赏令 查看可接取的任务。"
        
        progress = active["current_progress"]
        target = active["target_count"]
        expire_time = active["expire_time"]
        remaining = max(0, expire_time - int(time.time()))
        
        rewards = json.loads(active["rewards"])
        
        return True, (
            f"📜 当前悬赏\n"
            f"━━━━━━━━━━━━━━━\n"
            f"任务：{active['bounty_name']}\n"
            f"进度：{progress}/{target}\n"
            f"奖励：{rewards.get('stone', 0):,} 灵石 + {rewards.get('exp', 0):,} 修为\n"
            f"剩余时间：{remaining // 60} 分钟\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💡 使用 /完成悬赏 提交任务"
        )
    
    async def complete_bounty(self, player: Player) -> Tuple[bool, str]:
        """完成悬赏任务（事务保护）"""
        # 使用事务保护，防止并发领取和奖励发放不一致
        await self.db.conn.execute("BEGIN IMMEDIATE")
        try:
            # 重新获取任务状态（事务内）
            active = await self.db.ext.get_active_bounty(player.user_id)
            if not active:
                await self.db.conn.rollback()
                return False, "你当前没有进行中的悬赏任务。"
            
            # 检查是否超时
            if int(time.time()) > active["expire_time"]:
                await self.db.conn.execute(
                    "UPDATE bounty_tasks SET status = 0 WHERE user_id = ? AND status = 1",
                    (player.user_id,)
                )
                await self.db.conn.commit()
                return False, "悬赏任务已超时，自动取消。"
            
            # 检查任务进度是否达到目标
            progress = active.get("current_progress", 0)
            target = active.get("target_count", 1)
            if progress < target:
                await self.db.conn.rollback()
                return False, (
                    f"❌ 任务尚未完成！\n"
                    f"任务：{active['bounty_name']}\n"
                    f"进度：{progress}/{target}\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"💡 通过历练、秘境探索等方式完成任务目标"
                )
            
            rewards = json.loads(active["rewards"])
            stone_reward = rewards.get("stone", 0)
            exp_reward = rewards.get("exp", 0)
            
            # 先标记任务完成（防止并发重复领取）
            await self.db.conn.execute(
                "UPDATE bounty_tasks SET status = 2 WHERE user_id = ? AND status = 1",
                (player.user_id,)
            )
            
            # 发放奖励（带整数溢出保护）
            MAX_VALUE = 2**63 - 1  # SQLite INTEGER 最大值
            player.gold = min(player.gold + stone_reward, MAX_VALUE)
            player.experience = min(player.experience + exp_reward, MAX_VALUE)
            await self.db.conn.execute(
                "UPDATE players SET gold = ?, experience = ? WHERE user_id = ?",
                (player.gold, player.experience, player.user_id)
            )
            
            # 提交事务
            await self.db.conn.commit()
            
        except Exception as e:
            await self.db.conn.rollback()
            raise
        
        # 物品奖励（事务外处理，失败不影响主奖励）
        item_msg = ""
        if self.storage_ring_manager:
            try:
                bounty_type = active.get("target_type", "gather")
                dropped_items = await self._roll_bounty_items(player, bounty_type)
                if dropped_items:
                    item_lines = []
                    for item_name, count in dropped_items:
                        success, _ = await self.storage_ring_manager.store_item(player, item_name, count, silent=True)
                        if success:
                            item_lines.append(f"  · {item_name} x{count}")
                        else:
                            item_lines.append(f"  · {item_name} x{count}（储物戒已满，丢失）")
                    if item_lines:
                        item_msg = "\n\n📦 获得物品：\n" + "\n".join(item_lines)
            except Exception:
                pass
        
        return True, (
            f"✅ 悬赏完成！\n"
            f"任务：{active['bounty_name']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"获得灵石：+{stone_reward:,}\n"
            f"获得修为：+{exp_reward:,}{item_msg}"
        )
    
    async def abandon_bounty(self, player: Player) -> Tuple[bool, str]:
        """放弃悬赏任务（带冷却惩罚）"""
        active = await self.db.ext.get_active_bounty(player.user_id)
        if not active:
            return False, "你当前没有进行中的悬赏任务。"
        
        # 放弃任务后设置30分钟冷却（防止刷取高奖励任务）
        await self.db.ext.cancel_bounty(player.user_id)
        
        # 记录放弃时间用于冷却检查
        abandon_cooldown = int(time.time()) + 1800  # 30分钟冷却
        cd_key = f"bounty_abandon_cd_{player.user_id}"
        await self.db.ext.set_system_config(cd_key, str(abandon_cooldown))
        
        return True, f"已放弃悬赏：{active['bounty_name']}\n⚠️ 30分钟内无法接取新悬赏"
    
    async def _roll_bounty_items(self, player: Player, bounty_type: str) -> List[Tuple[str, int]]:
        """
        根据悬赏类型随机掉落物品
        
        Args:
            player: 玩家对象
            bounty_type: 悬赏类型
            
        Returns:
            掉落物品列表 [(物品名, 数量), ...]
        """
        dropped_items = []
        
        # 获取对应类型的掉落表
        drop_table = BOUNTY_ITEM_REWARDS.get(bounty_type, BOUNTY_ITEM_REWARDS["gather"])
        
        # 悬赏完成70%概率获得物品
        if random.randint(1, 100) > 70:
            return dropped_items
        
        # 加权随机选择物品
        total_weight = sum(item["weight"] for item in drop_table)
        roll = random.randint(1, total_weight)
        
        current_weight = 0
        for item in drop_table:
            current_weight += item["weight"]
            if roll <= current_weight:
                count = random.randint(item["min"], item["max"])
                dropped_items.append((item["name"], count))
                break
        
        return dropped_items
    
    async def add_bounty_progress(self, player: Player, activity_type: str, count: int = 1) -> Tuple[bool, str]:
        """
        根据活动类型增加悬赏进度（带输入验证和并发保护）
        
        Args:
            player: 玩家对象
            activity_type: 活动类型 (adventure/rift/kill/gather/explore/escort/collect)
            count: 增加的进度数量（必须为正整数，最大为10）
            
        Returns:
            (是否有进度更新, 消息)
        """
        # 输入验证：防止负数、零、超大值
        if not isinstance(count, int) or count <= 0:
            return False, ""
        count = min(count, 10)  # 单次最多增加10进度，防止刷取
        
        # 活动类型白名单验证
        type_mapping = {
            "adventure": ["kill", "gather", "explore"],
            "rift": ["explore"],
            "kill": ["kill"],
            "gather": ["gather"],
            "explore": ["explore"],
            "escort": ["escort"],
            "collect": ["collect"],
        }
        if activity_type not in type_mapping:
            return False, ""
        
        # 使用事务保护，防止并发刷进度
        await self.db.conn.execute("BEGIN IMMEDIATE")
        try:
            # 事务内获取最新状态
            active = await self.db.ext.get_active_bounty(player.user_id)
            if not active:
                await self.db.conn.rollback()
                return False, ""
            
            # 检查是否超时
            if int(time.time()) > active["expire_time"]:
                await self.db.conn.rollback()
                return False, ""
            
            bounty_type = active.get("target_type", "")
            current_progress = active.get("current_progress", 0)
            target = active.get("target_count", 1)
            
            # 如果已完成则不再增加
            if current_progress >= target:
                await self.db.conn.rollback()
                return False, ""
            
            valid_types = type_mapping.get(activity_type, [])
            if bounty_type not in valid_types:
                await self.db.conn.rollback()
                return False, ""
            
            # 原子更新进度（使用SQL计算，防止TOCTOU）
            new_progress = min(current_progress + count, target)
            await self.db.conn.execute(
                "UPDATE bounty_tasks SET current_progress = ? WHERE user_id = ? AND status = 1 AND current_progress = ?",
                (new_progress, player.user_id, current_progress)
            )
            await self.db.conn.commit()
            
            if new_progress >= target:
                return True, f"\n\n📜 悬赏【{active['bounty_name']}】已完成！使用 /完成悬赏 领取奖励"
            else:
                return True, f"\n\n📜 悬赏进度：{new_progress}/{target}"
        except Exception:
            await self.db.conn.rollback()
            raise
    
    async def check_and_expire_bounties(self) -> int:
        """检查并处理过期悬赏任务
        
        Returns:
            处理的过期任务数量
        """
        now = int(time.time())
        
        # 将过期的进行中任务标记为失败(status=3)
        cursor = await self.db.conn.execute(
            "UPDATE bounty_tasks SET status = 3 WHERE status = 1 AND expire_time < ?",
            (now,)
        )
        await self.db.conn.commit()
        
        # 返回受影响的行数
        return cursor.rowcount
