# handlers/social_handlers.py
"""社交互动处理器"""
import re
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..managers.social_manager import SocialManager


class SocialHandlers:
    """社交互动处理器"""
    
    def __init__(self, db: DataBase, social_mgr: SocialManager):
        self.db = db
        self.social_mgr = social_mgr
    
    def _get_at_from_message(self, event: AstrMessageEvent) -> str:
        """从消息中提取@的用户ID"""
        try:
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
            # 也尝试匹配 [At:xxx] 格式
            at_match = re.search(r'\[At:(\d+)\]', raw_msg)
            if at_match:
                return at_match.group(1)
        except Exception:
            pass
        
        return ""
    
    def _extract_target_id(self, event: AstrMessageEvent, target: str) -> str:
        """提取目标用户ID"""
        # 先尝试从@中获取
        at_id = self._get_at_from_message(event)
        if at_id:
            return at_id
        
        # 再尝试从参数中获取
        if target:
            target = target.strip()
            # 移除@符号
            if target.startswith("@"):
                target = target[1:]
            # 移除可能的CQ码残留
            target = re.sub(r'\[CQ:[^\]]+\]', '', target).strip()
            target = re.sub(r'\[At:\d+\]', '', target).strip()
            # 只取第一个参数（空格分隔）
            parts = target.split()
            return parts[0].strip() if parts else target.strip()
        return ""
    
    # ========== 拜师收徒 ==========
    
    async def handle_recruit(self, event: AstrMessageEvent, target: str = ""):
        """收徒"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        # 从原始消息解析参数
        raw_msg = event.get_message_str().strip()
        if raw_msg.startswith("/收徒"):
            raw_msg = raw_msg[3:].strip()
        elif raw_msg.startswith("收徒"):
            raw_msg = raw_msg[2:].strip()
        
        target_id = self._extract_target_id(event, raw_msg or target)
        if not target_id:
            yield event.plain_result("❌ 请指定目标：/收徒 @某人/道号")
            return
        
        success, msg = await self.social_mgr.request_apprentice(player, target_id)
        yield event.plain_result(msg)
    
    async def handle_apprentice(self, event: AstrMessageEvent, target: str = ""):
        """拜师"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        # 从原始消息解析参数
        raw_msg = event.get_message_str().strip()
        if raw_msg.startswith("/拜师"):
            raw_msg = raw_msg[3:].strip()
        elif raw_msg.startswith("拜师"):
            raw_msg = raw_msg[2:].strip()
        
        target_id = self._extract_target_id(event, raw_msg or target)
        
        # 如果没有指定目标，尝试接受收徒请求
        if not target_id:
            success, msg = await self.social_mgr.accept_apprentice(user_id)
            yield event.plain_result(msg)
            return
        
        success, msg = await self.social_mgr.request_master(player, target_id)
        yield event.plain_result(msg)
    
    async def handle_accept_master(self, event: AstrMessageEvent):
        """接受师徒请求"""
        user_id = event.get_sender_id()
        success, msg = await self.social_mgr.accept_apprentice(user_id)
        yield event.plain_result(msg)
    
    async def handle_leave_master(self, event: AstrMessageEvent):
        """离开师门"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        success, msg = await self.social_mgr.leave_master(player)
        yield event.plain_result(msg)
    
    async def handle_master_info(self, event: AstrMessageEvent):
        """查看师徒信息"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        msg = await self.social_mgr.get_master_info(user_id)
        yield event.plain_result(msg)
    
    # ========== 道侣系统 ==========
    
    async def handle_propose(self, event: AstrMessageEvent, target: str = ""):
        """求道侣"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        # 从原始消息解析参数
        raw_msg = event.get_message_str().strip()
        if raw_msg.startswith("/求道侣"):
            raw_msg = raw_msg[4:].strip()
        elif raw_msg.startswith("求道侣"):
            raw_msg = raw_msg[3:].strip()
        
        target_id = self._extract_target_id(event, raw_msg or target)
        if not target_id:
            yield event.plain_result("❌ 请指定目标：/求道侣 @某人/道号")
            return
        
        success, msg = await self.social_mgr.propose(player, target_id)
        yield event.plain_result(msg)
    
    async def handle_accept_couple(self, event: AstrMessageEvent):
        """接受道侣"""
        user_id = event.get_sender_id()
        success, msg = await self.social_mgr.accept_couple(user_id)
        yield event.plain_result(msg)
    
    async def handle_reject_couple(self, event: AstrMessageEvent):
        """拒绝道侣"""
        user_id = event.get_sender_id()
        success, msg = await self.social_mgr.reject_couple(user_id)
        yield event.plain_result(msg)
    
    async def handle_divorce(self, event: AstrMessageEvent):
        """解除道侣"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        success, msg = await self.social_mgr.divorce(player)
        yield event.plain_result(msg)
    
    async def handle_couple_info(self, event: AstrMessageEvent):
        """查看道侣信息"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        msg = await self.social_mgr.get_couple_info(user_id)
        yield event.plain_result(msg)
    
    # ========== 论道系统 ==========
    
    async def handle_debate(self, event: AstrMessageEvent, target: str = ""):
        """论道"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        # 从原始消息解析参数
        raw_msg = event.get_message_str().strip()
        if raw_msg.startswith("/论道"):
            raw_msg = raw_msg[3:].strip()
        elif raw_msg.startswith("论道"):
            raw_msg = raw_msg[2:].strip()
        
        target_id = self._extract_target_id(event, raw_msg or target)
        if not target_id:
            yield event.plain_result("❌ 请指定目标：/论道 @某人/道号")
            return
        
        success, msg = await self.social_mgr.debate(player, target_id)
        yield event.plain_result(msg)
    
    async def handle_social_help(self, event: AstrMessageEvent):
        """社交帮助"""
        help_text = """
👥 社交互动帮助
━━━━━━━━━━━━━━━

👨‍👩‍👧‍👦【师徒系统】
  收徒 @某人 - 收对方为徒
  拜师 @某人 - 拜对方为师
  拜师 - 接受收徒请求
  师徒信息 - 查看师徒关系
  离开师门 - 脱离师门
  
  📈 徒弟修炼+10%加成
  📈 师父获得徒弟修为5%

💕【道侣系统】
  求道侣 @某人 - 求道侣(5000灵石)
  接受道侣 - 接受请求
  拒绝道侣 - 拒绝请求
  道侣信息 - 查看道侣
  解除道侣 - 分手
  
  📈 双方修炼+15%加成
  📈 双修效果x1.2

📜【论道系统】
  论道 @某人 - 与对方论道
  
  📈 双方都获得修为奖励
  ⏰ 冷却1小时
        """.strip()
        yield event.plain_result(help_text)
