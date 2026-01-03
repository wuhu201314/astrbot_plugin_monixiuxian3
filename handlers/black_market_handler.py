# handlers/black_market_handler.py
"""黑市处理器 - 可购买所有丹药但价格翻倍，每日限购5颗"""
import re
import time
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from ..data import DataBase
from ..core import PillManager
from ..models import Player
from ..config_manager import ConfigManager
from .utils import player_required

__all__ = ["BlackMarketHandler"]

# 黑市配置
BLACK_MARKET_PRICE_MULTIPLIER = 2.0  # 价格翻倍（贵100%）
DAILY_PURCHASE_LIMIT = 5  # 每日限购数量


class BlackMarketHandler:
    """黑市处理器"""
    
    def __init__(self, db: DataBase, config_manager: ConfigManager):
        self.db = db
        self.config_manager = config_manager
        self.pill_manager = PillManager(db, config_manager)
        self._all_pills = None
    
    def _get_all_pills(self) -> list:
        """获取所有丹药配置"""
        if self._all_pills is None:
            pills = []
            # 从 pills_data 获取破境丹
            for name, pill in self.config_manager.pills_data.items():
                pills.append(pill)
            # 从 exp_pills_data 获取修为丹
            for name, pill in self.config_manager.exp_pills_data.items():
                pills.append(pill)
            # 从 utility_pills_data 获取功能丹
            for name, pill in self.config_manager.utility_pills_data.items():
                pills.append(pill)
            self._all_pills = pills
        return self._all_pills
    
    def _get_black_market_price(self, original_price: int) -> int:
        """计算黑市价格"""
        return int(original_price * BLACK_MARKET_PRICE_MULTIPLIER)
    
    def _get_today_start_timestamp(self) -> int:
        """获取今天0点的时间戳"""
        now = time.time()
        # 获取今天0点
        today = time.localtime(now)
        today_start = time.mktime(time.struct_time((
            today.tm_year, today.tm_mon, today.tm_mday,
            0, 0, 0, today.tm_wday, today.tm_yday, today.tm_isdst
        )))
        return int(today_start)
    
    async def _get_today_purchase_count(self, user_id: str) -> int:
        """获取用户今日已购买数量"""
        today_start = self._get_today_start_timestamp()
        
        async with self.db.conn.execute(
            """SELECT COALESCE(SUM(quantity), 0) FROM black_market_purchases 
               WHERE user_id = ? AND purchase_time >= ?""",
            (user_id, today_start)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def _record_purchase(self, user_id: str, pill_name: str, quantity: int):
        """记录购买"""
        now = int(time.time())
        await self.db.conn.execute(
            """INSERT INTO black_market_purchases (user_id, pill_name, quantity, purchase_time)
               VALUES (?, ?, ?, ?)""",
            (user_id, pill_name, quantity, now)
        )
    
    async def _ensure_table_exists(self):
        """确保黑市购买记录表存在"""
        await self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS black_market_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                pill_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                purchase_time INTEGER NOT NULL
            )
        """)
        await self.db.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_black_market_user_time ON black_market_purchases(user_id, purchase_time)"
        )
    
    async def handle_black_market(self, event: AstrMessageEvent):
        """显示黑市丹药列表"""
        await self._ensure_table_exists()
        
        pills = self._get_all_pills()
        if not pills:
            yield event.plain_result("🏴 黑市暂无货物...")
            return
        
        # 获取用户今日购买数量
        user_id = event.get_sender_id()
        today_count = await self._get_today_purchase_count(user_id)
        remaining = max(0, DAILY_PURCHASE_LIMIT - today_count)
        
        lines = [
            "🏴 黑市·暗巷丹铺",
            "━━━━━━━━━━━━━━━",
            "⚠️ 所有丹药价格翻倍！",
            f"📦 今日限购：{remaining}/{DAILY_PURCHASE_LIMIT} 颗",
            "━━━━━━━━━━━━━━━",
        ]
        
        # 按品阶分组
        rank_groups = {}
        for pill in pills:
            rank = pill.get("rank", "未知")
            if rank not in rank_groups:
                rank_groups[rank] = []
            rank_groups[rank].append(pill)
        
        # 品阶排序
        rank_order = ["灵品", "珍品", "圣品", "帝品", "道品", "仙品", "神品"]
        
        for rank in rank_order:
            if rank in rank_groups:
                lines.append(f"\n【{rank}丹药】")
                for pill in rank_groups[rank]:
                    name = pill["name"]
                    original_price = pill["price"]
                    black_price = self._get_black_market_price(original_price)
                    lines.append(f"  {name} - {black_price:,}灵石")
        
        lines.extend([
            "",
            "━━━━━━━━━━━━━━━",
            "💡 /黑市购买 <丹药名> [数量]",
        ])
        
        yield event.plain_result("\n".join(lines))
    
    def _parse_buy_args(self, event: AstrMessageEvent) -> tuple:
        """从原始消息解析购买参数"""
        try:
            raw_msg = event.get_message_str().strip()
            if raw_msg.startswith('/'):
                raw_msg = raw_msg[1:]
            
            if raw_msg.startswith("黑市购买"):
                raw_msg = raw_msg[4:].strip()
            
            if not raw_msg:
                return "", 1
            
            raw_msg = raw_msg.replace("　", " ")
            raw_msg = raw_msg.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
            
            # x数量 格式
            match = re.match(r'^(.+?)[xX＊*]\s*(\d+)$', raw_msg)
            if match:
                return match.group(1).strip(), int(match.group(2))
            
            # 空格+数量 格式
            match = re.match(r'^(.+?)\s+(\d+)$', raw_msg)
            if match:
                return match.group(1).strip(), int(match.group(2))
            
            return raw_msg.strip(), 1
        except Exception:
            return "", 1
    
    @player_required
    async def handle_black_market_buy(self, player: Player, event: AstrMessageEvent, item_name: str = "", quantity: int = 1):
        """黑市购买丹药"""
        await self._ensure_table_exists()
        
        # 解析参数
        parsed_name, parsed_qty = self._parse_buy_args(event)
        if parsed_name:
            item_name = parsed_name
            quantity = parsed_qty
        
        if not item_name:
            yield event.plain_result("❌ 请指定要购买的丹药，例如：/黑市购买 筑基丹")
            return
        
        if quantity <= 0:
            quantity = 1
        
        # 检查每日限购
        today_count = await self._get_today_purchase_count(player.user_id)
        remaining = DAILY_PURCHASE_LIMIT - today_count
        
        if remaining <= 0:
            yield event.plain_result(
                f"❌ 今日购买已达上限！\n"
                f"每日限购：{DAILY_PURCHASE_LIMIT} 颗\n"
                f"💡 明日再来吧~"
            )
            return
        
        if quantity > remaining:
            yield event.plain_result(
                f"❌ 购买数量超出限制！\n"
                f"今日剩余额度：{remaining} 颗\n"
                f"请求购买：{quantity} 颗"
            )
            return
        
        # 查找丹药
        pills = self._get_all_pills()
        target_pill = None
        for pill in pills:
            if pill["name"] == item_name:
                target_pill = pill
                break
        
        if not target_pill:
            yield event.plain_result(f"❌ 黑市没有【{item_name}】这种丹药。")
            return
        
        # 计算价格
        original_price = target_pill["price"]
        black_price = self._get_black_market_price(original_price)
        total_price = black_price * quantity
        
        if player.gold < total_price:
            yield event.plain_result(
                f"❌ 灵石不足！\n"
                f"【{item_name}】黑市价: {black_price:,} 灵石\n"
                f"购买数量: {quantity}\n"
                f"需要灵石: {total_price:,}\n"
                f"你的灵石: {player.gold:,}"
            )
            return
        
        # 执行购买
        await self.db.conn.execute("BEGIN IMMEDIATE")
        try:
            player = await self.db.get_player_by_id(player.user_id)
            if player.gold < total_price:
                await self.db.conn.rollback()
                yield event.plain_result(f"❌ 灵石不足！需要 {total_price:,} 灵石。")
                return
            
            # 添加丹药
            await self.pill_manager.add_pill_to_inventory(player, item_name, count=quantity)
            
            # 扣除灵石
            await self.db.conn.execute(
                "UPDATE players SET gold = gold - ? WHERE user_id = ?",
                (total_price, player.user_id)
            )
            player.gold -= total_price
            
            # 记录购买
            await self._record_purchase(player.user_id, item_name, quantity)
            
            await self.db.conn.commit()
            
            new_remaining = remaining - quantity
            qty_str = f"x{quantity}" if quantity > 1 else ""
            yield event.plain_result(
                f"🏴 黑市交易成功！\n"
                f"━━━━━━━━━━━━━━━\n"
                f"购买：【{item_name}】{qty_str}\n"
                f"花费：{total_price:,} 灵石\n"
                f"剩余：{player.gold:,} 灵石\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📦 今日剩余额度：{new_remaining}/{DAILY_PURCHASE_LIMIT}"
            )
            
        except Exception as e:
            await self.db.conn.rollback()
            logger.error(f"黑市购买异常: {e}")
            yield event.plain_result(f"❌ 交易失败，请稍后重试。")
