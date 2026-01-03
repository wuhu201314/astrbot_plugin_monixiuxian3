# handlers/tower_handlers.py
"""通天塔处理器"""
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..managers.tower_manager import TowerManager


class TowerHandlers:
    """通天塔处理器"""
    
    def __init__(self, db: DataBase, tower_mgr: TowerManager):
        self.db = db
        self.tower_mgr = tower_mgr
    
    async def handle_challenge(self, event: AstrMessageEvent):
        """挑战通天塔"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        victory, msg, _ = await self.tower_mgr.challenge_floor(player)
        yield event.plain_result(msg)
    
    async def handle_speed_run(self, event: AstrMessageEvent, floors: int = 10):
        """速通通天塔"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        if floors < 1:
            floors = 10
        
        success, msg, _ = await self.tower_mgr.speed_run(player, floors)
        yield event.plain_result(msg)
    
    async def handle_tower_info(self, event: AstrMessageEvent):
        """查看通天塔信息"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        msg = await self.tower_mgr.get_tower_info(user_id)
        yield event.plain_result(msg)
    
    async def handle_boss_info(self, event: AstrMessageEvent):
        """查看下层Boss信息"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        msg = await self.tower_mgr.get_next_boss_info(player)
        yield event.plain_result(msg)
    
    async def handle_floor_ranking(self, event: AstrMessageEvent):
        """通天塔层数排行榜"""
        msg = await self.tower_mgr.get_floor_ranking()
        yield event.plain_result(msg)
    
    async def handle_points_ranking(self, event: AstrMessageEvent):
        """通天塔积分排行榜"""
        msg = await self.tower_mgr.get_points_ranking()
        yield event.plain_result(msg)
    
    async def handle_shop(self, event: AstrMessageEvent):
        """通天塔商店"""
        msg = self.tower_mgr.get_shop_info()
        yield event.plain_result(msg)
    
    async def handle_exchange(self, event: AstrMessageEvent, item_id: int = 0):
        """兑换商品"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("❌ 你还没有开始修仙！")
            return
        
        if item_id <= 0:
            yield event.plain_result("❌ 请输入商品编号！例如：/通天塔兑换 1")
            return
        
        success, msg = await self.tower_mgr.exchange_item(player, item_id)
        yield event.plain_result(msg)
    
    async def handle_tower_help(self, event: AstrMessageEvent):
        """通天塔帮助"""
        help_text = """
═══ 通天塔帮助 ═══

【挑战通天塔】 - 挑战通天塔下一层
【速通通天塔】 - 连续挑战10层，可指定层数
【通天塔信息】 - 查看当前通天塔进度
【通天塔BOSS】 - 查看下层BOSS属性
【通天塔排行榜】 - 查看通天塔排行榜
【通天塔积分排行榜】 - 查看积分排行榜
【通天塔商店】 - 查看通天塔商店商品
【通天塔兑换 编号】 - 兑换商店商品

════════════
通天塔规则说明：
1. 每周一0点重置所有用户层数
2. 每周一0点重置商店限购
3. 每10层可获得额外奖励
════════════
积分获取方式：
1. 每通关1层获得100积分
2. 每通关10层额外获得500积分
════════════
输入对应命令开始你的通天塔之旅吧！
        """.strip()
        yield event.plain_result(help_text)
