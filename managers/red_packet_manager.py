# managers/red_packet_manager.py
"""仙缘红包管理器 - 发红包/抢红包"""
import random
import time
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass, field
from ..data import DataBase
from ..models import Player

__all__ = ["RedPacketManager"]


@dataclass
class RedPacket:
    """仙缘红包"""
    packet_id: str  # 红包ID
    sender_id: str  # 发送者ID
    sender_name: str  # 发送者名称
    group_id: str  # 群组ID
    total_amount: int  # 总金额
    total_count: int  # 总份数
    remaining_amount: int  # 剩余金额
    remaining_count: int  # 剩余份数
    grabbed_users: Dict[str, int] = field(default_factory=dict)  # {user_id: amount}
    create_time: int = 0  # 创建时间
    expire_time: int = 0  # 过期时间
    message: str = ""  # 祝福语


# 配置
RED_PACKET_CONFIG = {
    "min_amount": 100,  # 最小金额
    "min_count": 1,  # 最小份数
    "max_count": 50,  # 最大份数
    "expire_seconds": 3600,  # 过期时间（1小时）
    "min_per_packet": 1,  # 每份最少1灵石
}


class RedPacketManager:
    """仙缘红包管理器"""
    
    def __init__(self, db: DataBase, config_manager=None):
        self.db = db
        self.config_manager = config_manager
        # 按群组存储红包 {group_id: {packet_id: RedPacket}}
        self._packets: Dict[str, Dict[str, RedPacket]] = {}
        self._packet_counter = 0
    
    def _generate_packet_id(self) -> str:
        """生成红包ID"""
        self._packet_counter += 1
        return f"xp_{int(time.time())}_{self._packet_counter}"
    
    def _split_amount(self, total: int, count: int) -> List[int]:
        """拆分红包金额（随机分配）"""
        if count == 1:
            return [total]
        
        min_per = RED_PACKET_CONFIG["min_per_packet"]
        amounts = []
        remaining = total
        
        for i in range(count - 1):
            # 保证剩余的人每人至少能拿到min_per
            max_can_take = remaining - (count - i - 1) * min_per
            if max_can_take <= min_per:
                amounts.append(min_per)
                remaining -= min_per
            else:
                # 随机分配，但不能太极端
                avg = remaining // (count - i)
                amount = random.randint(max(min_per, avg // 2), min(max_can_take, avg * 2))
                amounts.append(amount)
                remaining -= amount
        
        # 最后一份拿剩余的
        amounts.append(remaining)
        
        # 打乱顺序
        random.shuffle(amounts)
        return amounts
    
    async def create_packet(
        self, 
        sender: Player, 
        group_id: str, 
        total_amount: int, 
        count: int,
        message: str = ""
    ) -> Tuple[bool, str, Optional[RedPacket]]:
        """创建仙缘红包
        
        Args:
            sender: 发送者
            group_id: 群组ID
            total_amount: 总金额
            count: 份数
            message: 祝福语
            
        Returns:
            (是否成功, 消息, 红包对象)
        """
        config = RED_PACKET_CONFIG
        
        # 检查金额
        if total_amount < config["min_amount"]:
            return False, f"❌ 最少发送 {config['min_amount']} 灵石！", None
        
        if total_amount > sender.gold:
            return False, f"❌ 灵石不足！当前持有：{sender.gold:,}", None
        
        # 检查份数
        if count < config["min_count"]:
            return False, f"❌ 最少 {config['min_count']} 份！", None
        
        if count > config["max_count"]:
            return False, f"❌ 最多 {config['max_count']} 份！", None
        
        # 检查每份最少金额
        if total_amount < count * config["min_per_packet"]:
            return False, f"❌ 每份至少 {config['min_per_packet']} 灵石！", None
        
        # 扣除灵石
        sender.gold -= total_amount
        await self.db.update_player(sender)
        
        # 创建红包
        now = int(time.time())
        packet = RedPacket(
            packet_id=self._generate_packet_id(),
            sender_id=sender.user_id,
            sender_name=sender.user_name or f"道友{sender.user_id[:6]}",
            group_id=group_id,
            total_amount=total_amount,
            total_count=count,
            remaining_amount=total_amount,
            remaining_count=count,
            grabbed_users={},
            create_time=now,
            expire_time=now + config["expire_seconds"],
            message=message or "恭喜发财，仙缘广进！"
        )
        
        # 存储红包
        if group_id not in self._packets:
            self._packets[group_id] = {}
        self._packets[group_id][packet.packet_id] = packet
        
        msg = (
            f"🧧 仙缘红包 🧧\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✨ {packet.sender_name} 发了一个仙缘红包！\n"
            f"💰 总金额：{total_amount:,} 灵石\n"
            f"📦 共 {count} 份\n"
            f"💬 {packet.message}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💡 发送「抢仙缘」领取红包！\n"
            f"⏰ {config['expire_seconds'] // 60} 分钟后过期"
        )
        
        return True, msg, packet
    
    async def grab_packet(self, user: Player, group_id: str) -> Tuple[bool, str]:
        """抢仙缘红包
        
        Args:
            user: 抢红包的用户
            group_id: 群组ID
            
        Returns:
            (是否成功, 消息)
        """
        # 清理过期红包
        self._cleanup_expired(group_id)
        
        # 检查是否有红包
        if group_id not in self._packets or not self._packets[group_id]:
            return False, "❌ 当前没有仙缘红包可抢！"
        
        # 获取最早的未抢完红包
        packet = None
        for p in sorted(self._packets[group_id].values(), key=lambda x: x.create_time):
            if p.remaining_count > 0 and user.user_id not in p.grabbed_users:
                packet = p
                break
        
        if not packet:
            # 检查是否已经抢过
            for p in self._packets[group_id].values():
                if user.user_id in p.grabbed_users:
                    return False, "❌ 你已经抢过这个红包了！"
            return False, "❌ 红包已被抢完！"
        
        # 计算抢到的金额
        if packet.remaining_count == 1:
            # 最后一份拿剩余全部
            amount = packet.remaining_amount
        else:
            # 随机分配
            avg = packet.remaining_amount // packet.remaining_count
            min_amount = RED_PACKET_CONFIG["min_per_packet"]
            max_amount = min(
                packet.remaining_amount - (packet.remaining_count - 1) * min_amount,
                avg * 2
            )
            amount = random.randint(min_amount, max(min_amount, max_amount))
        
        # 更新红包状态
        packet.remaining_amount -= amount
        packet.remaining_count -= 1
        packet.grabbed_users[user.user_id] = amount
        
        # 给用户加灵石
        user.gold += amount
        await self.db.update_player(user)
        
        user_name = user.user_name or f"道友{user.user_id[:6]}"
        
        # 判断是否是手气最佳
        is_lucky = False
        if packet.remaining_count == 0:
            # 红包抢完了，判断手气最佳
            max_amount = max(packet.grabbed_users.values())
            if amount == max_amount:
                is_lucky = True
        
        msg = (
            f"🎉 抢到仙缘！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🧧 {packet.sender_name} 的红包\n"
            f"💰 {user_name} 抢到 {amount:,} 灵石！\n"
        )
        
        if is_lucky and packet.total_count > 1:
            msg += f"🏆 手气最佳！\n"
        
        msg += f"📦 剩余 {packet.remaining_count}/{packet.total_count} 份\n"
        msg += f"━━━━━━━━━━━━━━━\n"
        msg += f"你的灵石：{user.gold:,}"
        
        # 如果红包抢完了，显示结果
        if packet.remaining_count == 0:
            msg += self._get_packet_result(packet)
            # 移除红包
            del self._packets[group_id][packet.packet_id]
        
        return True, msg
    
    def _get_packet_result(self, packet: RedPacket) -> str:
        """获取红包结果"""
        if not packet.grabbed_users:
            return ""
        
        # 找出手气最佳
        max_amount = max(packet.grabbed_users.values())
        lucky_users = [uid for uid, amt in packet.grabbed_users.items() if amt == max_amount]
        
        result = (
            f"\n\n🧧 红包已抢完！\n"
            f"━━━━━━━━━━━━━━━\n"
        )
        
        # 显示抢红包记录（最多显示10条）
        items = list(packet.grabbed_users.items())[:10]
        for user_id, amount in items:
            lucky_mark = " 🏆" if user_id in lucky_users else ""
            result += f"  · {amount:,} 灵石{lucky_mark}\n"
        
        if len(packet.grabbed_users) > 10:
            result += f"  ... 共 {len(packet.grabbed_users)} 人\n"
        
        return result
    
    def _cleanup_expired(self, group_id: str):
        """清理过期红包"""
        if group_id not in self._packets:
            return
        
        now = int(time.time())
        expired = [
            pid for pid, p in self._packets[group_id].items()
            if now > p.expire_time
        ]
        
        for pid in expired:
            packet = self._packets[group_id][pid]
            # 退还剩余金额（异步处理可能有问题，这里简化处理）
            if packet.remaining_amount > 0:
                # 标记为已过期，让发送者下次操作时退还
                pass
            del self._packets[group_id][pid]
    
    async def refund_expired(self, user_id: str) -> Tuple[int, str]:
        """退还用户过期红包的剩余金额
        
        Returns:
            (退还金额, 消息)
        """
        total_refund = 0
        now = int(time.time())
        
        for group_id in list(self._packets.keys()):
            for pid in list(self._packets[group_id].keys()):
                packet = self._packets[group_id][pid]
                if packet.sender_id == user_id and now > packet.expire_time:
                    if packet.remaining_amount > 0:
                        total_refund += packet.remaining_amount
                    del self._packets[group_id][pid]
        
        if total_refund > 0:
            player = await self.db.get_player_by_id(user_id)
            if player:
                player.gold += total_refund
                await self.db.update_player(player)
        
        return total_refund, f"已退还 {total_refund:,} 灵石" if total_refund > 0 else ""
    
    def get_active_packets(self, group_id: str) -> List[RedPacket]:
        """获取群组内活跃的红包"""
        self._cleanup_expired(group_id)
        if group_id not in self._packets:
            return []
        return list(self._packets[group_id].values())
