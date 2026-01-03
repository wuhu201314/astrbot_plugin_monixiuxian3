# handlers/gold_interaction_handlers.py
"""灵石互动处理器"""
import re
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..managers.gold_interaction_manager import GoldInteractionManager


class GoldInteractionHandlers:
    """灵石互动处理器"""
    
    def __init__(self, db: DataBase, gold_interaction_mgr: GoldInteractionManager):
        self.db = db
        self.gold_interaction_mgr = gold_interaction_mgr
    
    def _extract_target_id(self, target_str: str) -> str:
        """从字符串中提取用户ID"""
        if not target_str:
            return ""
        target_str = target_str.strip()
        # 移除@符号
        if target_str.startswith("@"):
            target_str = target_str[1:]
        # 移除可能的空格
        target_str = target_str.strip()
        return target_str
    
    def _get_at_from_message(self, event: AstrMessageEvent) -> str:
        """从消息中提取@的用户ID"""
        try:
            # 尝试使用 get_ats 方法
            if hasattr(event, 'get_ats'):
                at_list = event.get_ats()
                if at_list:
                    return str(at_list[0])
        except Exception:
            pass
        
        # 从原始消息中解析 [CQ:at,qq=xxx] 格式
        try:
            raw_msg = event.get_message_str()
            at_match = re.search(r'\[CQ:at,qq=(\d+)\]', raw_msg)
            if at_match:
                return at_match.group(1)
        except Exception:
            pass
        
        return ""
    
    async def handle_gift_gold(self, event: AstrMessageEvent, args: str = ""):
        """赠送灵石"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        # 从原始消息中解析参数
        raw_msg = event.get_message_str().strip()
        # 移除命令前缀
        if raw_msg.startswith("/送灵石"):
            raw_msg = raw_msg[4:].strip()
        elif raw_msg.startswith("送灵石"):
            raw_msg = raw_msg[3:].strip()
        
        # 如果原始消息解析失败，尝试使用传入的args
        if not raw_msg and args:
            raw_msg = args.strip()
        
        if not raw_msg:
            yield event.plain_result("❌ 请输入：/送灵石 @某人/道号 数量")
            return
        
        # 尝试从消息中获取@的用户
        target_id = self._get_at_from_message(event)
        
        if target_id:
            # 有@，从raw_msg中提取数量（最后一个数字）
            parts = raw_msg.split()
            amount_str = parts[-1] if parts else ""
        else:
            # 没有@，尝试解析 "道号/ID 数量" 格式
            parts = raw_msg.split()
            if len(parts) < 2:
                yield event.plain_result("❌ 请输入：/送灵石 @某人/道号 数量")
                return
            target_id = self._extract_target_id(parts[0])
            amount_str = parts[-1]
        
        # 解析数量
        try:
            amount = int(amount_str)
        except ValueError:
            yield event.plain_result("❌ 请输入有效的数量！")
            return
        
        if amount <= 0:
            yield event.plain_result("❌ 数量必须大于0！")
            return
        
        success, msg = await self.gold_interaction_mgr.gift_gold(player, target_id, amount)
        yield event.plain_result(msg)
    
    async def handle_steal_gold(self, event: AstrMessageEvent, target: str = ""):
        """偷窃灵石"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        # 从原始消息中解析参数
        raw_msg = event.get_message_str().strip()
        if raw_msg.startswith("/偷灵石"):
            raw_msg = raw_msg[4:].strip()
        elif raw_msg.startswith("偷灵石"):
            raw_msg = raw_msg[3:].strip()
        
        if not raw_msg and target:
            raw_msg = target.strip()
        
        # 获取目标ID - 只取第一个参数
        target_id = self._get_at_from_message(event)
        if not target_id:
            # 取第一个空格前的内容作为目标
            parts = raw_msg.split()
            target_id = self._extract_target_id(parts[0]) if parts else ""
        
        if not target_id:
            yield event.plain_result("❌ 请指定目标：/偷灵石 @某人/道号")
            return
        
        success, msg = await self.gold_interaction_mgr.steal_gold(player, target_id)
        yield event.plain_result(msg)
    
    async def handle_rob_gold(self, event: AstrMessageEvent, target: str = ""):
        """抢夺灵石"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        # 从原始消息中解析参数
        raw_msg = event.get_message_str().strip()
        if raw_msg.startswith("/抢灵石"):
            raw_msg = raw_msg[4:].strip()
        elif raw_msg.startswith("抢灵石"):
            raw_msg = raw_msg[3:].strip()
        
        if not raw_msg and target:
            raw_msg = target.strip()
        
        # 获取目标ID - 只取第一个参数
        target_id = self._get_at_from_message(event)
        if not target_id:
            # 取第一个空格前的内容作为目标
            parts = raw_msg.split()
            target_id = self._extract_target_id(parts[0]) if parts else ""
        
        if not target_id:
            yield event.plain_result("❌ 请指定目标：/抢灵石 @某人/道号")
            return
        
        success, msg = await self.gold_interaction_mgr.rob_gold(player, target_id)
        yield event.plain_result(msg)
    
    async def handle_interaction_info(self, event: AstrMessageEvent):
        """查看灵石互动说明"""
        info = self.gold_interaction_mgr.get_interaction_info()
        yield event.plain_result(info)
