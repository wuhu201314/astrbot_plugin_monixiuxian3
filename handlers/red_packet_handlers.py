# handlers/red_packet_handlers.py
"""仙缘红包处理器"""
import re
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..managers.red_packet_manager import RedPacketManager


class RedPacketHandlers:
    """仙缘红包处理器"""
    
    def __init__(self, db: DataBase, red_packet_mgr: RedPacketManager):
        self.db = db
        self.red_packet_mgr = red_packet_mgr
    
    async def handle_send_packet(self, event: AstrMessageEvent, args: str = ""):
        """发送仙缘红包
        
        格式: /送仙缘 金额 份数 [祝福语]
        例如: /送仙缘 1000 10 恭喜发财
        """
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        
        if not group_id:
            yield event.plain_result("❌ 仙缘红包只能在群聊中发送！")
            return
        
        player = await self.db.get_player_by_id(user_id)
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        # 从原始消息中解析参数（AstrBot的args参数可能不完整）
        raw_msg = event.get_message_str().strip()
        # 移除命令前缀，支持 /送仙缘 或 送仙缘
        if raw_msg.startswith("/送仙缘"):
            raw_msg = raw_msg[4:].strip()
        elif raw_msg.startswith("送仙缘"):
            raw_msg = raw_msg[3:].strip()
        
        # 如果原始消息解析失败，尝试使用传入的args
        if not raw_msg and args:
            raw_msg = args.strip()
        
        # 解析参数
        if not raw_msg:
            yield event.plain_result(
                "🧧 仙缘红包使用说明\n"
                "━━━━━━━━━━━━━━━\n"
                "发送格式：/送仙缘 金额 份数 [祝福语]\n"
                "例如：/送仙缘 1000 10 恭喜发财\n"
                "━━━━━━━━━━━━━━━\n"
                "💰 最少 100 灵石\n"
                "📦 份数 1-50 份\n"
                "⏰ 1小时后过期"
            )
            return
        
        parts = raw_msg.split(maxsplit=2)
        if len(parts) < 2:
            yield event.plain_result("❌ 请输入：/送仙缘 金额 份数 [祝福语]")
            return
        
        try:
            total_amount = int(parts[0])
            count = int(parts[1])
        except ValueError:
            yield event.plain_result("❌ 金额和份数必须是数字！")
            return
        
        message = parts[2] if len(parts) > 2 else ""
        
        success, msg, packet = await self.red_packet_mgr.create_packet(
            player, group_id, total_amount, count, message
        )
        yield event.plain_result(msg)
    
    async def handle_grab_packet(self, event: AstrMessageEvent):
        """抢仙缘红包"""
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        
        if not group_id:
            yield event.plain_result("❌ 仙缘红包只能在群聊中抢！")
            return
        
        player = await self.db.get_player_by_id(user_id)
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        # 先检查是否有过期红包需要退还
        refund_amount, refund_msg = await self.red_packet_mgr.refund_expired(user_id)
        
        success, msg = await self.red_packet_mgr.grab_packet(player, group_id)
        
        # 如果有退款，附加到消息
        if refund_amount > 0:
            msg = f"💰 {refund_msg}\n\n{msg}"
        
        yield event.plain_result(msg)
    
    async def handle_packet_info(self, event: AstrMessageEvent):
        """查看仙缘红包说明"""
        info = (
            "🧧 仙缘红包系统 🧧\n"
            "━━━━━━━━━━━━━━━\n"
            "\n"
            "📤 发送红包\n"
            "  /送仙缘 金额 份数 [祝福语]\n"
            "  例：/送仙缘 1000 10 恭喜发财\n"
            "\n"
            "📥 抢红包\n"
            "  /抢仙缘\n"
            "\n"
            "━━━━━━━━━━━━━━━\n"
            "📋 规则说明\n"
            "  💰 最少发送 100 灵石\n"
            "  📦 份数范围 1-50 份\n"
            "  ⏰ 红包 1 小时后过期\n"
            "  🔄 过期未抢完自动退还\n"
            "  🏆 抢完后显示手气最佳\n"
            "  ⚠️ 每个红包只能抢一次\n"
            "━━━━━━━━━━━━━━━\n"
            "💡 红包金额随机分配，试试你的手气！"
        )
        yield event.plain_result(info)
