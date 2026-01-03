# handlers/tribulation_handlers.py
"""天劫系统处理器"""
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase
from ..managers.tribulation_manager import TribulationManager


class TribulationHandlers:
    """天劫系统处理器"""
    
    def __init__(self, db: DataBase, tribulation_mgr: TribulationManager):
        self.db = db
        self.tribulation_mgr = tribulation_mgr
    
    async def handle_tribulation_info(self, event: AstrMessageEvent):
        """查看天劫信息"""
        user_id = event.get_sender_id()
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield event.plain_result("你还没有开始修仙，请先使用「我要修仙」开始你的修仙之旅！")
            return
        
        # 获取下一境界
        from ..config_manager import ConfigManager
        config_mgr = self.tribulation_mgr.config_manager
        if config_mgr:
            level_data = config_mgr.get_level_data(player.cultivation_type)
            if player.level_index < len(level_data) - 1:
                next_level = player.level_index + 1
                preview = self.tribulation_mgr.get_tribulation_preview(player, next_level)
            else:
                preview = "你已达到最高境界，无需再渡天劫。"
        else:
            preview = "配置加载失败，无法获取天劫信息。"
        
        info = (
            f"⚡ 天劫系统 ⚡\n"
            f"━━━━━━━━━━━━━━━\n"
            f"当前境界：{player.level_index}\n"
            f"触发境界：金丹期（13级）以上\n"
            f"\n【天劫类型】\n"
            f"• 雷劫：九天神雷降临\n"
            f"• 火劫：三昧真火焚身\n"
            f"• 风劫：罡风裂体\n"
            f"• 心劫：心魔入侵\n"
            f"{preview}"
        )
        
        yield event.plain_result(info)
