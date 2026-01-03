# handlers/bank_handlers.py
"""灵石银行处理器 - 包含存取款、贷款、流水查询功能"""
import time
import re
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..managers.bank_manager import BankManager
from ..models import Player
from .utils import player_required

__all__ = ["BankHandlers"]


class BankHandlers:
    """灵石银行处理器"""
    
    def __init__(self, db: DataBase, bank_mgr: BankManager):
        self.db = db
        self.bank_mgr = bank_mgr
    
    def _parse_amount_from_message(self, event: AstrMessageEvent, command: str) -> int:
        """从原始消息中解析金额参数
        
        Args:
            event: 消息事件
            command: 命令名称（如 "存灵石"、"取灵石"）
            
        Returns:
            解析出的金额，解析失败返回0
        """
        try:
            raw_msg = event.get_message_str().strip()
            # 移除命令前缀 / 或其他
            if raw_msg.startswith('/'):
                raw_msg = raw_msg[1:]
            
            # 移除命令本身
            if raw_msg.startswith(command):
                raw_msg = raw_msg[len(command):].strip()
            
            # 尝试解析数字
            if raw_msg:
                # 支持 "全部" 或 "all" 关键字
                if raw_msg.lower() in ['全部', 'all', '所有']:
                    return -1  # 特殊值表示全部
                
                # 提取数字
                match = re.match(r'^(\d+)', raw_msg)
                if match:
                    return int(match.group(1))
            
            return 0
        except Exception:
            return 0
    
    @player_required
    async def handle_bank_info(self, player: Player, event: AstrMessageEvent):
        """查看银行信息"""
        info = await self.bank_mgr.get_bank_info(player)
        
        msg_lines = [
            "🏦 灵石银行",
            "━━━━━━━━━━━━━━━",
            f"💰 存款余额：{info['balance']:,} 灵石",
            f"📈 待领利息：{info['pending_interest']:,} 灵石",
            f"📊 日利率：0.1%（复利）",
            "━━━━━━━━━━━━━━━",
            f"💎 持有灵石：{player.gold:,}",
        ]
        
        # 显示贷款信息
        if info.get("loan"):
            loan_info = await self.bank_mgr.get_loan_info(player)
            if loan_info:
                loan_type_name = "突破贷款" if loan_info["loan_type"] == "breakthrough" else "普通贷款"
                status = "⚠️ 已逾期！" if loan_info["is_overdue"] else f"剩余 {loan_info['days_remaining']} 天"
                msg_lines.extend([
                    "━━━━━━━━━━━━━━━",
                    f"📋 当前贷款（{loan_type_name}）",
                    f"   本金：{loan_info['principal']:,} 灵石",
                    f"   当前利息：{loan_info['current_interest']:,} 灵石",
                    f"   应还总额：{loan_info['total_due']:,} 灵石",
                    f"   状态：{status}",
                ])
        
        msg_lines.extend([
            "━━━━━━━━━━━━━━━",
            "💡 指令：",
            "  /存灵石 <数量>",
            "  /取灵石 <数量>",
            "  /领取利息",
            "  /贷款 <数量>",
            "  /还款",
            "  /银行流水",
        ])
        
        yield event.plain_result("\n".join(msg_lines))
    
    @player_required
    async def handle_deposit(self, player: Player, event: AstrMessageEvent, amount: int = 0):
        """存入灵石"""
        # 从原始消息解析金额
        if amount <= 0:
            amount = self._parse_amount_from_message(event, "存灵石")
        
        if amount <= 0:
            yield event.plain_result("❌ 请输入存款金额，例如：/存灵石 10000")
            return
        
        success, msg = await self.bank_mgr.deposit(player, amount)
        prefix = "✅" if success else "❌"
        yield event.plain_result(f"{prefix} {msg}")
    
    @player_required
    async def handle_withdraw(self, player: Player, event: AstrMessageEvent, amount: int = 0):
        """取出灵石"""
        # 从原始消息解析金额
        if amount <= 0:
            amount = self._parse_amount_from_message(event, "取灵石")
        
        # 处理 "全部" 关键字
        if amount == -1:
            bank_data = await self.bank_mgr.db.ext.get_bank_account(player.user_id)
            if bank_data and bank_data["balance"] > 0:
                amount = bank_data["balance"]
            else:
                yield event.plain_result("❌ 银行余额为0，无法取款。")
                return
        
        if amount <= 0:
            yield event.plain_result("❌ 请输入取款金额，例如：/取灵石 10000\n💡 也可以输入 /取灵石 全部")
            return
        
        success, msg = await self.bank_mgr.withdraw(player, amount)
        prefix = "✅" if success else "❌"
        yield event.plain_result(f"{prefix} {msg}")
    
    @player_required
    async def handle_claim_interest(self, player: Player, event: AstrMessageEvent):
        """领取利息"""
        success, msg = await self.bank_mgr.claim_interest(player)
        prefix = "✅" if success else "❌"
        yield event.plain_result(f"{prefix} {msg}")
    
    @player_required
    async def handle_loan(self, player: Player, event: AstrMessageEvent, amount: int = 0):
        """申请贷款"""
        # 从原始消息解析金额
        if amount <= 0:
            amount = self._parse_amount_from_message(event, "贷款")
        
        if amount <= 0:
            # 显示贷款帮助
            yield event.plain_result(
                "🏦 贷款说明\n"
                "━━━━━━━━━━━━━━━\n"
                "📌 普通贷款：\n"
                "   日利率：0.5%\n"
                "   期限：7天\n"
                "   额度：1,000 - 1,000,000 灵石\n"
                "━━━━━━━━━━━━━━━\n"
                "💀 逾期后果：被银行追杀致死！\n"
                "   所有修为和装备将化为虚无\n"
                "━━━━━━━━━━━━━━━\n"
                "💡 用法：/贷款 <金额>\n"
                "   例如：/贷款 50000"
            )
            return
        
        success, msg = await self.bank_mgr.borrow(player, amount, "normal")
        yield event.plain_result(msg)
    
    @player_required
    async def handle_repay(self, player: Player, event: AstrMessageEvent):
        """还款"""
        success, msg = await self.bank_mgr.repay(player)
        yield event.plain_result(msg)
    
    @player_required
    async def handle_transactions(self, player: Player, event: AstrMessageEvent):
        """查看银行流水"""
        transactions = await self.bank_mgr.get_transactions(player.user_id, 15)
        
        if not transactions:
            yield event.plain_result("📋 暂无交易记录")
            return
        
        msg_lines = [
            "📋 银行交易流水（最近15条）",
            "━━━━━━━━━━━━━━━",
        ]
        
        type_names = {
            "deposit": "💰 存入",
            "withdraw": "💸 取出",
            "interest": "📈 利息",
            "loan": "📥 贷款",
            "repay": "📤 还款",
            "overdue_penalty": "⚠️ 逾期",
        }
        
        for trans in transactions:
            trans_time = time.strftime("%m-%d %H:%M", time.localtime(trans["created_at"]))
            type_name = type_names.get(trans["trans_type"], trans["trans_type"])
            amount = trans["amount"]
            amount_str = f"+{amount:,}" if amount > 0 else f"{amount:,}"
            
            msg_lines.append(f"{trans_time} {type_name} {amount_str}")
        
        msg_lines.extend([
            "━━━━━━━━━━━━━━━",
            f"当前余额：{transactions[0]['balance_after']:,} 灵石" if transactions else ""
        ])
        
        yield event.plain_result("\n".join(msg_lines))
    
    @player_required
    async def handle_breakthrough_loan(self, player: Player, event: AstrMessageEvent, amount: int = 0):
        """申请突破贷款（用于购买破境丹）"""
        # 从原始消息解析金额
        if amount <= 0:
            amount = self._parse_amount_from_message(event, "突破贷款")
        
        if amount <= 0:
            yield event.plain_result(
                "🏦 突破贷款说明\n"
                "━━━━━━━━━━━━━━━\n"
                "📌 专为突破准备的短期贷款：\n"
                "   日利率：0.8%（较高）\n"
                "   期限：3天（较短）\n"
                "   额度：1,000 - 1,000,000 灵石\n"
                "━━━━━━━━━━━━━━━\n"
                "✨ 突破成功后自动还款\n"
                "━━━━━━━━━━━━━━━\n"
                "💀 逾期后果：被银行追杀致死！\n"
                "   所有修为和装备将化为虚无\n"
                "━━━━━━━━━━━━━━━\n"
                "💡 用法：/突破贷款 <金额>"
            )
            return
        
        success, msg = await self.bank_mgr.borrow(player, amount, "breakthrough")
        yield event.plain_result(msg)
