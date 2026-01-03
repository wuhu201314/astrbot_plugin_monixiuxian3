# handlers/blessed_land_handlers.py
"""洞天福地处理器"""
import re
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..managers.blessed_land_manager import BlessedLandManager
from ..models import Player
from .utils import player_required

__all__ = ["BlessedLandHandlers"]


class BlessedLandHandlers:
    """洞天福地处理器"""
    
    def __init__(self, db: DataBase, blessed_land_mgr: BlessedLandManager):
        self.db = db
        self.mgr = blessed_land_mgr
    
    def _parse_land_type_from_message(self, event: AstrMessageEvent) -> int:
        """从原始消息中解析洞天类型"""
        try:
            raw_msg = event.get_message_str().strip()
            # 移除命令前缀
            if raw_msg.startswith('/'):
                raw_msg = raw_msg[1:]
            
            # 移除命令本身
            if raw_msg.startswith("购买洞天"):
                raw_msg = raw_msg[4:].strip()
            
            # 提取数字
            if raw_msg:
                match = re.match(r'^(\d+)', raw_msg)
                if match:
                    return int(match.group(1))
            return 0
        except Exception:
            return 0
    
    @player_required
    async def handle_blessed_land_info(self, player: Player, event: AstrMessageEvent):
        """查看洞天信息"""
        info = await self.mgr.get_blessed_land_info(player.user_id)
        yield event.plain_result(info)
    
    @player_required
    async def handle_purchase(self, player: Player, event: AstrMessageEvent, land_type: int = 0):
        """购买洞天"""
        # 从原始消息解析洞天类型
        if land_type <= 0:
            land_type = self._parse_land_type_from_message(event)
        
        if land_type <= 0:
            yield event.plain_result(
                "🏔️ 购买洞天\n"
                "━━━━━━━━━━━━━━━\n"
                "1. 小洞天 - 10,000灵石 (+5%修炼)\n"
                "2. 中洞天 - 50,000灵石 (+10%修炼)\n"
                "3. 大洞天 - 200,000灵石 (+20%修炼)\n"
                "4. 福地 - 500,000灵石 (+30%修炼)\n"
                "5. 洞天福地 - 1,000,000灵石 (+50%修炼)\n"
                "━━━━━━━━━━━━━━━\n"
                "💡 使用 /购买洞天 <编号>"
            )
            return
        
        success, msg = await self.mgr.purchase_blessed_land(player, land_type)
        yield event.plain_result(msg)
    
    @player_required
    async def handle_upgrade(self, player: Player, event: AstrMessageEvent):
        """升级洞天"""
        success, msg = await self.mgr.upgrade_blessed_land(player)
        yield event.plain_result(msg)
    
    @player_required
    async def handle_collect(self, player: Player, event: AstrMessageEvent):
        """收取洞天产出"""
        success, msg = await self.mgr.collect_income(player)
        yield event.plain_result(msg)
