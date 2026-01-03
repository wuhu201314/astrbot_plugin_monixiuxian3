# handlers/fortune_handlers.py
"""福缘系统处理器"""
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..managers.fortune_manager import FortuneManager


class FortuneHandlers:
    """福缘系统处理器"""
    
    def __init__(self, db: DataBase, fortune_mgr: FortuneManager):
        self.db = db
        self.fortune_mgr = fortune_mgr
    
    async def handle_fortune_info(self, event: AstrMessageEvent):
        """查看福缘信息"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("你还没有开始修仙，请先使用「我要修仙」开始你的修仙之旅！")
            return
        
        info = self.fortune_mgr.get_fortune_info(player)
        yield event.plain_result(info)
    
    async def handle_claim_fortune(self, event: AstrMessageEvent):
        """求福缘"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("你还没有开始修仙，请先使用「我要修仙」开始你的修仙之旅！")
            return
        
        success, msg = await self.fortune_mgr.claim_daily_fortune(player)
        yield event.plain_result(msg)
