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
            "=== 修仙指令 (v2.0.1) ===\n"
            "\n"
            "【基础 & 修炼】\n"
            "我要修仙 [灵修/体修] | 我的信息\n"
            "签到 | 闭关 | 出关\n"
            "突破信息 | 突破 [丹药名]\n"
            "我的装备 | 装备/卸下 <装备名>\n"
            "丹药背包 | 服用丹药 <丹药名>\n"
            "\n"
            "【交易 & 管理】\n"
            "丹阁 | 器阁 | 百宝阁\n"
            "购买 <物品名> [数量]\n"
            "储物戒 | 存入/取出/丢弃 <物品名>\n"
            "赠予 <@某人> <物品> | 接收/拒绝\n"
            "\n"
            "【宗门系统】\n"
            "创建宗门 <名> | 加入宗门 <名>\n"
            "我的宗门 | 宗门列表 | 退出宗门\n"
            "宗门捐献 <数> | 宗门任务\n"
            "宗门管理: 踢出/传位/职位变更\n"
            "\n"
            "【战斗 & 竞技】\n"
            "切磋 <@某人> (无损) | 决斗 (死斗)\n"
            "世界Boss | 挑战Boss\n"
            "排行榜: 境界/战力/灵石/宗门排行\n"
            "\n"
            "【历练 & 生产】\n"
            "开始历练 | 历练状态 | 完成历练\n"
            "秘境列表 | 探索秘境 <ID>\n"
            "丹药配方 | 炼丹 <ID>\n"
            "传承信息 (数值详情)\n"
            "================"
        )
        yield event.plain_result(help_text)
