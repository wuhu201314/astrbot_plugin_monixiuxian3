# handlers/player_handler.py
import time
import random
from datetime import datetime
from astrbot.api.event import AstrMessageEvent
from astrbot.api import AstrBotConfig
from ..data import DataBase
from ..core import CultivationManager, PillManager
from ..models import Player
from ..models_extended import UserStatus
from ..config_manager import ConfigManager
from .utils import player_required

CMD_START_XIUXIAN = "我要修仙"
CMD_PLAYER_INFO = "我的信息"
CMD_START_CULTIVATION = "闭关"
CMD_END_CULTIVATION = "出关"
CMD_CHECK_IN = "签到"

__all__ = ["PlayerHandler"]

class PlayerHandler:
    """玩家基础信息处理器 - 支持灵修/体修选择"""

    def __init__(self, db: DataBase, config: AstrBotConfig, config_manager: ConfigManager):
        self.db = db
        self.config = config
        self.config_manager = config_manager
        self.cultivation_manager = CultivationManager(config, config_manager)
        self.pill_manager = PillManager(self.db, self.config_manager)
        self.enlightenment_manager = None  # 延迟初始化
        self.inner_demon_manager = None  # 延迟初始化
        self.fortune_manager = None  # 延迟初始化

    def set_immersive_managers(self, enlightenment_mgr, inner_demon_mgr, fortune_mgr):
        """设置沉浸式修仙系统管理器"""
        self.enlightenment_manager = enlightenment_mgr
        self.inner_demon_manager = inner_demon_mgr
        self.fortune_manager = fortune_mgr

    async def handle_start_xiuxian(self, event: AstrMessageEvent, cultivation_type: str = ""):
        """处理创建角色

        Args:
            cultivation_type: 修炼类型，"灵修"或"体修"，为空则显示选择提示
        """
        user_id = event.get_sender_id()

        # 检查是否已创建角色
        if await self.db.get_player_by_id(user_id):
            yield event.plain_result("道友，你已踏入仙途，无需重复此举。")
            return

        # 如果没有提供职业选择，显示选择提示
        if not cultivation_type or cultivation_type.strip() == "":
            help_msg = (
                "🌟 欢迎踏入修仙之路！\n"
                "━━━━━━━━━━━━━━━\n"
                "请选择你的修炼方式：\n\n"
                "【灵修】以灵气为主，法术攻击\n"
                "• 寿命：100\n"
                "• 灵气：100-1000\n"
                "• 法伤：5-100\n"
                "• 物伤：5\n"
                "• 法防：0\n"
                "• 物防：5\n"
                "• 精神力：100-500\n\n"
                "【体修】以气血为主，肉身强横\n"
                "• 寿命：50-100\n"
                "• 气血：100-500\n"
                "• 法伤：0\n"
                "• 物伤：100-500\n"
                "• 法防：50-200\n"
                "• 物防：100-500\n"
                "• 精神力：100-500\n"
                "━━━━━━━━━━━━━━━\n"
                "⚠️ 修仙风险警告 ⚠️\n"
                "• 突破失败有概率走火入魔身死道消\n"
                "• 生命值归零也会导致死亡\n"
                "• 死亡后所有数据清除，需重新入仙途\n"
                "━━━━━━━━━━━━━━━\n"
                f"💡 使用方法：\n"
                f"  {CMD_START_XIUXIAN} 灵修\n"
                f"  {CMD_START_XIUXIAN} 体修"
            )
            yield event.plain_result(help_msg)
            return

        # 验证职业类型
        cultivation_type = cultivation_type.strip()
        if cultivation_type not in ["灵修", "体修"]:
            yield event.plain_result(f"职业选择错误！请选择「灵修」或「体修」。")
            return

        # 生成新玩家
        new_player = self.cultivation_manager.generate_new_player_stats(user_id, cultivation_type)
        await self.db.create_player(new_player)

        # 获取灵根描述
        root_name = new_player.spiritual_root.replace("灵根", "")
        root_description = self.cultivation_manager._get_root_description(root_name)

        reply_msg = (
            f"🎉 恭喜道友 {event.get_sender_name()} 踏上仙途！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"修炼方式：【{new_player.cultivation_type}】\n"
            f"灵根：【{new_player.spiritual_root}】\n"
            f"评价：{root_description}\n"
            f"启动资金：{new_player.gold} 灵石\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚠️ 修仙有风险，突破需谨慎！\n"
            f"突破失败或生命值归零会导致\n"
            f"身死道消，所有数据清除！\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💡 发送「{CMD_PLAYER_INFO}」查看状态"
        )
        yield event.plain_result(reply_msg)

    @player_required
    async def handle_player_info(self, player: Player, event: AstrMessageEvent):
        """处理查看玩家信息 - 展示新属性"""
        display_name = event.get_sender_name()
        required_exp = player.get_required_exp(self.config_manager)

        # 更新丹药效果并计算最终属性倍率
        await self.pill_manager.update_temporary_effects(player)
        pill_multipliers = self.pill_manager.calculate_pill_attribute_effects(player)

        # 获取装备加成后的属性
        from ..core import EquipmentManager
        equipment_manager = EquipmentManager(self.db, self.config_manager)
        equipped_items = equipment_manager.get_equipped_items(
            player,
            self.config_manager.items_data,
            self.config_manager.weapons_data
        )
        total_attrs = player.get_total_attributes(equipped_items, pill_multipliers)

        # 图片生成暂时禁用（缺少资源文件会导致效果很差）
        # 直接使用优化后的文本格式显示

        # 文本模式 (完整信息显示)
        
        # 获取战力（综合攻防）
        combat_power = (
            int(total_attrs['physical_damage']) + int(total_attrs['magic_damage']) +
            int(total_attrs['physical_defense']) + int(total_attrs['magic_defense']) +
            int(total_attrs['mental_power']) // 10
        )
        
        # 获取宗门信息
        sect_name = "无宗门"
        position_name = "散修"
        if player.sect_id and player.sect_id != 0:
            sect = await self.db.ext.get_sect_by_id(player.sect_id)
            if sect:
                sect_name = sect.sect_name
                if sect.sect_owner == player.user_id:
                    position_name = "宗主"
                elif player.sect_position == 1:
                    position_name = "长老"
                elif player.sect_position == 2:
                    position_name = "亲传弟子"
                elif player.sect_position == 3:
                    position_name = "内门弟子"
                else:
                    position_name = "外门弟子"
        
        # 获取装备信息
        weapon_name = player.weapon if player.weapon else "无"
        armor_name = player.armor if player.armor else "无"
        technique_name = player.main_technique if player.main_technique else "无"
        
        # 获取突破状态
        breakthrough_rate = f"+{player.level_up_rate}%" if player.level_up_rate > 0 else "0%"
        
        # 构建信息显示
        dao_hao = player.user_name if player.user_name else display_name
        
        reply_msg = (
            f"📋 道友 {dao_hao} 的信息\n"
            f"━━━━━━━━━━━━━━━\n"
            f"\n"
            f"【基本信息】\n"
            f"  道号：{dao_hao}\n"
            f"  境界：{player.get_level(self.config_manager)}\n"
            f"  修为：{int(player.experience):,}/{int(required_exp):,}\n"
            f"  灵石：{player.gold:,}\n"
            f"  战力：{combat_power:,}\n"
            f"  灵根：{player.spiritual_root}\n"
            f"  突破加成：{breakthrough_rate}\n"
            f"\n"
            f"【修炼属性】\n"
            f"  修炼方式：{player.cultivation_type}\n"
            f"  状态：{player.state}\n"
            f"  寿命：{player.lifespan}\n"
            f"  精神力：{total_attrs['mental_power']}\n"
        )
        
        # 根据修炼类型添加不同属性
        if player.cultivation_type == "体修":
            reply_msg += (
                f"  气血：{player.blood_qi}/{total_attrs.get('max_blood_qi', 0)}\n"
                f"  物伤：{total_attrs['physical_damage']}\n"
                f"  法伤：{total_attrs['magic_damage']}\n"
                f"  物防：{total_attrs['physical_defense']}\n"
                f"  法防：{total_attrs['magic_defense']}\n"
            )
        else:
            reply_msg += (
                f"  灵气：{player.spiritual_qi}/{total_attrs.get('max_spiritual_qi', 0)}\n"
                f"  法伤：{total_attrs['magic_damage']}\n"
                f"  物伤：{total_attrs['physical_damage']}\n"
                f"  法防：{total_attrs['magic_defense']}\n"
                f"  物防：{total_attrs['physical_defense']}\n"
            )
        
        reply_msg += (
            f"\n"
            f"【装备信息】\n"
            f"  主修功法：{technique_name}\n"
            f"  法器：{weapon_name}\n"
            f"  防具：{armor_name}\n"
            f"\n"
            f"【宗门信息】\n"
            f"  所在宗门：{sect_name}\n"
            f"  宗门职位：{position_name}\n"
        )
        
        # 获取贷款信息
        loan = await self.db.ext.get_active_loan(player.user_id)
        if loan:
            now = int(time.time())
            remaining_seconds = loan["due_at"] - now
            remaining_days = remaining_seconds // 86400
            remaining_hours = (remaining_seconds % 86400) // 3600
            
            days_borrowed = max(1, (now - loan["borrowed_at"]) // 86400)
            interest = int(loan["principal"] * loan["interest_rate"] * days_borrowed)
            total_due = loan["principal"] + interest
            
            loan_type_name = "突破贷款" if loan["loan_type"] == "breakthrough" else "普通贷款"
            
            if remaining_seconds <= 0:
                time_str = "⚠️ 已逾期！"
            elif remaining_days <= 0:
                time_str = f"🔴 {remaining_hours}小时"
            elif remaining_days <= 1:
                time_str = f"🟠 {remaining_days}天{remaining_hours}小时"
            else:
                time_str = f"🟡 {remaining_days}天"
            
            reply_msg += (
                f"\n"
                f"【贷款信息】💰\n"
                f"  类型：{loan_type_name}\n"
                f"  应还：{total_due:,} 灵石\n"
                f"  剩余：{time_str}\n"
                f"  💀 逾期将被追杀致死！\n"
            )
        
        reply_msg += "━━━━━━━━━━━━━━━"
        
        yield event.plain_result(reply_msg)

    @player_required
    async def handle_start_cultivation(self, player: Player, event: AstrMessageEvent):
        """处理闭关指令"""
        # 检查是否已经在闭关
        if player.state == "修炼中":
            yield event.plain_result("道友已在闭关中，请勿重复进入。")
            return
        
        # 检查是否在其他活动中（历练、秘境探索等）
        user_cd = await self.db.ext.get_user_cd(player.user_id)
        if user_cd and user_cd.type != UserStatus.IDLE:
            current_status = UserStatus.get_name(user_cd.type)
            yield event.plain_result(f"❌ 道友当前正{current_status}，无法闭关修炼！")
            return

        # 记录闭关开始时间
        player.state = "修炼中"
        player.cultivation_start_time = int(time.time())
        await self.db.update_player(player)
        await self.db.ext.set_user_busy(player.user_id, UserStatus.CULTIVATING, 0)

        yield event.plain_result(
            "🧘 道友已进入闭关状态\n"
            "━━━━━━━━━━━━━━━\n"
            "闭关期间，你将与世隔绝，潜心修炼。\n"
            f"💡 发送「{CMD_END_CULTIVATION}」结束闭关\n"
            "⏱️ 每分钟将获得修为，受灵根资质影响。"
        )

    @player_required
    async def handle_end_cultivation(self, player: Player, event: AstrMessageEvent):
        """处理出关指令"""
        # 检查是否在闭关中
        if player.state != "修炼中":
            yield event.plain_result("道友当前并未闭关，无需出关。")
            return

        # 检查是否有闭关开始时间
        if player.cultivation_start_time == 0:
            yield event.plain_result("数据异常：未记录闭关开始时间。")
            return

        # 计算闭关时长（分钟）
        end_time = int(time.time())
        duration_seconds = end_time - player.cultivation_start_time
        duration_minutes = duration_seconds // 60

        if duration_minutes < 1:
            yield event.plain_result("道友闭关时间不足1分钟，未获得修为。请继续闭关修炼。")
            return

        # 闭关时长上限根据境界调整（基础24小时，每提升一个大境界增加6小时）
        # level_index: 0-8练气, 9-17筑基, 18-26金丹, 27-35元婴, 36-44化神, 45-53炼虚, 54-62合体, 63-71大乘, 72+渡劫
        base_minutes = 1440  # 24小时
        realm_bonus = (player.level_index // 9) * 360  # 每个大境界增加6小时
        MAX_CULTIVATION_MINUTES = base_minutes + realm_bonus
        effective_minutes = min(duration_minutes, MAX_CULTIVATION_MINUTES)
        exceeded_time = duration_minutes > MAX_CULTIVATION_MINUTES

        # 更新丹药效果，确保持续结算
        await self.pill_manager.update_temporary_effects(player)
        pill_multipliers = self.pill_manager.calculate_pill_attribute_effects(player)

        # 获取主修心法的修为加成
        technique_bonus = 0.0
        if player.main_technique:
            from ..core import EquipmentManager
            equipment_manager = EquipmentManager(self.db, self.config_manager)
            equipped_items = equipment_manager.get_equipped_items(
                player,
                self.config_manager.items_data,
                self.config_manager.weapons_data
            )
            # 找到主修心法
            for item in equipped_items:
                if item.item_type == "main_technique":
                    technique_bonus = item.exp_multiplier
                    break

        # 计算获得的修为（使用有效时长）
        gained_exp = self.cultivation_manager.calculate_cultivation_exp(
            player,
            effective_minutes,
            technique_bonus,
            pill_multipliers
        )
        
        # 尝试触发悟道（沉浸式修仙系统）
        enlightenment_msg = ""
        if self.enlightenment_manager:
            triggered, msg, bonus_exp = await self.enlightenment_manager.try_enlightenment(player, gained_exp)
            if triggered:
                gained_exp += bonus_exp
                enlightenment_msg = f"\n\n{msg}"
        
        # 尝试触发心魔（沉浸式修仙系统）
        demon_msg = ""
        if self.inner_demon_manager:
            triggered, msg, demon_data = await self.inner_demon_manager.try_trigger_demon(player)
            if triggered:
                demon_msg = f"\n\n{msg}"
        
        # 尝试触发福缘（沉浸式修仙系统）
        fortune_msg = ""
        if self.fortune_manager:
            triggered, msg = await self.fortune_manager.try_fortune(player, "cultivation")
            if triggered:
                fortune_msg = f"\n\n{msg}"

        # 更新玩家数据
        player.experience += gained_exp
        player.state = "空闲"
        player.cultivation_start_time = 0
        
        # 闭关出关时恢复满HP（战斗属性）
        # HP是根据修为计算的，这里重新计算并恢复满
        from ..managers import CombatManager
        hp, mp = CombatManager.calculate_hp_mp(player.experience)
        old_hp = player.hp
        player.hp = hp
        player.mp = mp
        recovered_hp = hp - old_hp if old_hp > 0 else hp
        
        await self.db.update_player(player)
        await self.db.ext.set_user_free(player.user_id)

        # 计算闭关时长显示
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        time_str = ""
        if hours > 0:
            time_str += f"{hours}小时"
        if minutes > 0:
            time_str += f"{minutes}分钟"

        # 超时提示
        exceed_msg = ""
        if exceeded_time:
            effective_hours = MAX_CULTIVATION_MINUTES // 60
            exceed_msg = f"\n⚠️ 闭关超过{effective_hours}小时，仅计算前{effective_hours}小时修为"

        reply_msg = (
            "🌟 道友出关成功！\n"
            "━━━━━━━━━━━━━━━\n"
            f"⏱️ 闭关时长：{time_str}\n"
            f"📈 获得修为：{gained_exp:,}{exceed_msg}\n"
            f"💫 当前修为：{player.experience:,}\n"
            f"❤️ HP已恢复：{hp:,}\n"
            "━━━━━━━━━━━━━━━\n"
            "道友已回归红尘，可继续修行。"
        )
        
        # 添加沉浸式修仙系统消息
        reply_msg += enlightenment_msg + fortune_msg + demon_msg
        
        yield event.plain_result(reply_msg)

    @player_required
    async def handle_check_in(self, player: Player, event: AstrMessageEvent):
        """处理签到指令"""
        # 获取今天的日期（格式：YYYY-MM-DD）
        today = datetime.now().strftime("%Y-%m-%d")

        # 检查是否已经签到过
        if player.last_check_in_date == today:
            yield event.plain_result(
                "📅 道友今日已经签到过了\n"
                "请明日再来。"
            )
            return

        # 获取签到奖励范围配置
        check_in_gold_min = self.config["VALUES"].get("CHECK_IN_GOLD_MIN", 50)
        check_in_gold_max = self.config["VALUES"].get("CHECK_IN_GOLD_MAX", 500)

        # 确保最小值不大于最大值
        if check_in_gold_min > check_in_gold_max:
            check_in_gold_min, check_in_gold_max = check_in_gold_max, check_in_gold_min

        # 生成随机奖励
        check_in_gold = random.randint(check_in_gold_min, check_in_gold_max)

        # 更新玩家数据
        player.gold += check_in_gold
        player.last_check_in_date = today
        await self.db.update_player(player)

        reply_msg = (
            "✅ 签到成功！\n"
            "━━━━━━━━━━━━━━━\n"
            f"💰 获得灵石：{check_in_gold}\n"
            f"💎 当前灵石：{player.gold}\n"
            "━━━━━━━━━━━━━━━\n"
            "明日再来，莫要忘记哦~"
        )
        yield event.plain_result(reply_msg)

    # 逆天改命费用
    REROLL_ROOT_COST = 10000

    @player_required
    async def handle_reroll_root(self, player: Player, event: AstrMessageEvent):
        """处理逆天改命指令 - 重新生成灵根"""
        # 检查灵石是否足够
        if player.gold < self.REROLL_ROOT_COST:
            yield event.plain_result(
                f"❌ 灵石不足！\n"
                f"逆天改命需要 {self.REROLL_ROOT_COST:,} 灵石\n"
                f"当前灵石：{player.gold:,}"
            )
            return
        
        # 记录旧灵根
        old_root = player.spiritual_root
        old_root_name = old_root.replace("灵根", "")
        old_description = self.cultivation_manager._get_root_description(old_root_name)
        
        # 生成新灵根
        new_root = self.cultivation_manager._get_random_spiritual_root() + "灵根"
        new_root_name = new_root.replace("灵根", "")
        new_description = self.cultivation_manager._get_root_description(new_root_name)
        
        # 扣除灵石并更新灵根
        player.gold -= self.REROLL_ROOT_COST
        player.spiritual_root = new_root
        await self.db.update_player(player)
        
        # 判断是否变好了
        root_quality = self._get_root_quality(new_root_name)
        old_quality = self._get_root_quality(old_root_name)
        
        if root_quality > old_quality:
            result_emoji = "🎉"
            result_text = "天命改写，灵根蜕变！"
        elif root_quality < old_quality:
            result_emoji = "😢"
            result_text = "造化弄人，灵根退化..."
        else:
            result_emoji = "😐"
            result_text = "命运轮回，灵根更替。"
        
        reply_msg = (
            f"{result_emoji} 逆天改命！{result_emoji}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"消耗灵石：{self.REROLL_ROOT_COST:,}\n"
            f"\n"
            f"【原灵根】{old_root}\n"
            f"  {old_description}\n"
            f"\n"
            f"【新灵根】{new_root}\n"
            f"  {new_description}\n"
            f"\n"
            f"💫 {result_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"剩余灵石：{player.gold:,}"
        )
        yield event.plain_result(reply_msg)
    
    def _get_root_quality(self, root_name: str) -> int:
        """获取灵根品质等级（用于比较）"""
        # 品质从低到高
        quality_map = {
            # 废柴
            "伪": 0,
            # 四灵根
            "金木水火": 1, "金木水土": 1, "金木火土": 1, "金水火土": 1, "木水火土": 1,
            # 三灵根
            "金木水": 2, "金木火": 2, "金木土": 2, "金水火": 2, "金水土": 2,
            "金火土": 2, "木水火": 2, "木水土": 2, "木火土": 2, "水火土": 2,
            # 双灵根
            "金木": 3, "金水": 3, "金火": 3, "金土": 3, "木水": 3,
            "木火": 3, "木土": 3, "水火": 3, "水土": 3, "火土": 3,
            # 五行单灵根
            "金": 4, "木": 4, "水": 4, "火": 4, "土": 4,
            # 变异灵根
            "雷": 5, "冰": 5, "风": 5, "暗": 5, "光": 5,
            # 天灵根
            "天金": 6, "天木": 6, "天水": 6, "天火": 6, "天土": 6,
            # 混沌灵根
            "混沌": 7,
        }
        return quality_map.get(root_name, 3)  # 默认返回中等品质
