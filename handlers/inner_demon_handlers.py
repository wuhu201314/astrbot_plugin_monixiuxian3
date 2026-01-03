# handlers/inner_demon_handlers.py
"""心魔系统处理器"""
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..managers.inner_demon_manager import InnerDemonManager


class InnerDemonHandlers:
    """心魔系统处理器"""
    
    def __init__(self, db: DataBase, inner_demon_mgr: InnerDemonManager):
        self.db = db
        self.inner_demon_mgr = inner_demon_mgr
    
    async def handle_demon_info(self, event: AstrMessageEvent):
        """查看心魔信息"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("你还没有开始修仙，请先使用「我要修仙」开始你的修仙之旅！")
            return
        
        info = self.inner_demon_mgr.get_demon_info(player)
        yield event.plain_result(info)
    
    async def handle_demon_response(self, event: AstrMessageEvent, choice: str):
        """响应心魔"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("你还没有开始修仙，请先使用「我要修仙」开始你的修仙之旅！")
            return
        
        if not self.inner_demon_mgr.has_pending_demon(player):
            yield event.plain_result("你当前没有需要应对的心魔。")
            return
        
        success, msg = await self.inner_demon_mgr.respond_to_demon(player, choice)
        yield event.plain_result(msg)
