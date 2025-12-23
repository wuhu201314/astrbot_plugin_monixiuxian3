# handlers/misc_handler.py
from astrbot.api.event import AstrMessageEvent
from ..data import DataBase

__all__ = ["MiscHandler"]


class MiscHandler:
    """杂项指令处理器 - 提供帮助信息"""

    def __init__(self, db: DataBase):
        self.db = db

    async def handle_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = (
            "=== 修仙指令 ===\n"
            "\n"
            "【基础】\n"
            "我要修仙 [灵修/体修]\n"
            "我的信息\n"
            "签到\n"
            "\n"
            "【修炼】\n"
            "闭关\n"
            "出关\n"
            "突破信息\n"
            "突破 [丹药名]\n"
            "\n"
            "【装备】\n"
            "我的装备\n"
            "装备 <物品名>\n"
            "卸下 <装备名>\n"
            "\n"
            "【丹药】\n"
            "丹药背包\n"
            "丹药信息 <丹药名>\n"
            "服用丹药 <丹药名>\n"
            "\n"
            "【阁楼】\n"
            "丹阁\n"
            "器阁\n"
            "百宝阁\n"
            "购买 <物品名> [数量]\n"
            "\n"
            "【储物戒】\n"
            "储物戒\n"
            "存入 <物品名> [数量]\n"
            "取出 <物品名> [数量]\n"
            "丢弃 <物品名> [数量]\n"
            "赠予 <@某人/QQ号> <物品名> [数量]\n"
            "接收\n"
            "拒绝\n"
            "更换储物戒 [储物戒名]\n"
            "\n"
            "================"
        )
        yield event.plain_result(help_text)
