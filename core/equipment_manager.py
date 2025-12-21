# core/equipment_manager.py

from typing import Optional, List, Dict
from ..models import Player, Item
from ..data import DataBase

class EquipmentManager:
    """装备管理器 - 处理装备的穿戴、卸下和属性计算"""

    def __init__(self, db: DataBase):
        self.db = db

    def parse_item_from_name(self, item_name: str, items_data: dict, weapons_data: dict = None) -> Optional[Item]:
        """从物品名称解析为Item对象

        Args:
            item_name: 物品名称
            items_data: 物品配置数据字典
            weapons_data: 武器配置数据字典（可选）

        Returns:
            Item对象，如果未找到则返回None
        """
        if not item_name or item_name == "":
            return None

        # 先从物品配置中查找
        item_config = items_data.get(item_name)

        # 如果没找到且提供了武器配置，从武器配置中查找
        if not item_config and weapons_data:
            item_config = weapons_data.get(item_name)

        if not item_config:
            return None

        return Item(
            item_id=item_config.get("id", item_name),
            name=item_name,
            item_type=item_config.get("type", ""),
            description=item_config.get("description", ""),
            rank=item_config.get("rank", ""),
            required_level_index=item_config.get("required_level_index", 0),
            weapon_category=item_config.get("weapon_category", ""),
            magic_damage=item_config.get("magic_damage", 0),
            physical_damage=item_config.get("physical_damage", 0),
            magic_defense=item_config.get("magic_defense", 0),
            physical_defense=item_config.get("physical_defense", 0),
            mental_power=item_config.get("mental_power", 0),
            exp_multiplier=item_config.get("exp_multiplier", 0.0),
            spiritual_qi=item_config.get("spiritual_qi", 0),
            blood_qi=item_config.get("blood_qi", 0)
        )

    def get_equipped_items(self, player: Player, items_data: dict, weapons_data: dict = None) -> List[Item]:
        """获取玩家所有已装备的物品

        Args:
            player: 玩家对象
            items_data: 物品配置数据字典
            weapons_data: 武器配置数据字典（可选）

        Returns:
            已装备物品列表
        """
        equipped = []

        # 武器
        if player.weapon:
            item = self.parse_item_from_name(player.weapon, items_data, weapons_data)
            if item:
                equipped.append(item)

        # 防具
        if player.armor:
            item = self.parse_item_from_name(player.armor, items_data, weapons_data)
            if item:
                equipped.append(item)

        # 主修心法
        if player.main_technique:
            item = self.parse_item_from_name(player.main_technique, items_data, weapons_data)
            if item:
                equipped.append(item)

        # 功法列表
        techniques_list = player.get_techniques_list()
        for technique_name in techniques_list:
            item = self.parse_item_from_name(technique_name, items_data, weapons_data)
            if item:
                equipped.append(item)

        return equipped

    def check_equipment_level_requirement(self, player: Player, item: Item) -> tuple[bool, str]:
        """检查玩家是否满足装备的境界要求

        Args:
            player: 玩家对象
            item: 装备物品

        Returns:
            (是否满足, 提示消息)
        """
        if player.level_index < item.required_level_index:
            return False, f"境界不足！装备【{item.name}】（{item.rank}）需要达到境界索引 {item.required_level_index} 以上"
        return True, ""

    async def equip_item(self, player: Player, item: Item) -> tuple[bool, str]:
        """装备物品

        Args:
            player: 玩家对象
            item: 要装备的物品

        Returns:
            (是否成功, 消息)
        """
        # 检查境界要求
        can_equip, error_msg = self.check_equipment_level_requirement(player, item)
        if not can_equip:
            return False, error_msg

        # 根据物品类型装备到相应位置
        if item.item_type == "weapon":
            old_item = player.weapon
            player.weapon = item.name
            await self.db.update_player(player)
            if old_item:
                return True, f"已将【{old_item}】替换为【{item.name}】（{item.rank}）"
            else:
                return True, f"已装备武器【{item.name}】（{item.rank}）"

        elif item.item_type == "armor":
            old_item = player.armor
            player.armor = item.name
            await self.db.update_player(player)
            if old_item:
                return True, f"已将【{old_item}】替换为【{item.name}】（{item.rank}）"
            else:
                return True, f"已装备防具【{item.name}】（{item.rank}）"

        elif item.item_type == "main_technique":
            old_item = player.main_technique
            player.main_technique = item.name
            await self.db.update_player(player)
            if old_item:
                return True, f"已将主修心法【{old_item}】替换为【{item.name}】（{item.rank}）"
            else:
                return True, f"已装备主修心法【{item.name}】（{item.rank}）"

        elif item.item_type == "technique":
            techniques_list = player.get_techniques_list()

            # 检查是否已装备
            if item.name in techniques_list:
                return False, f"功法【{item.name}】已装备"

            # 检查功法栏是否已满（最多3个）
            if len(techniques_list) >= 3:
                return False, f"功法栏已满（最多3个），请先卸下其他功法"

            # 添加功法
            techniques_list.append(item.name)
            player.set_techniques_list(techniques_list)
            await self.db.update_player(player)
            return True, f"已装备功法【{item.name}】（{item.rank}）（{len(techniques_list)}/3）"

        else:
            return False, f"未知的装备类型：{item.item_type}"

    async def unequip_item(self, player: Player, slot_or_name: str) -> tuple[bool, str]:
        """卸下装备

        Args:
            player: 玩家对象
            slot_or_name: 装备槽位名称（武器/防具/主修心法）或功法名称

        Returns:
            (是否成功, 消息)
        """
        # 尝试按槽位卸下
        if slot_or_name in ["武器", "weapon"]:
            if not player.weapon:
                return False, "未装备武器"
            item_name = player.weapon
            player.weapon = ""
            await self.db.update_player(player)
            return True, f"已卸下武器【{item_name}】"

        elif slot_or_name in ["防具", "armor"]:
            if not player.armor:
                return False, "未装备防具"
            item_name = player.armor
            player.armor = ""
            await self.db.update_player(player)
            return True, f"已卸下防具【{item_name}】"

        elif slot_or_name in ["主修心法", "心法", "main_technique"]:
            if not player.main_technique:
                return False, "未装备主修心法"
            item_name = player.main_technique
            player.main_technique = ""
            await self.db.update_player(player)
            return True, f"已卸下主修心法【{item_name}】"

        # 尝试从功法列表中卸下（按名称）
        techniques_list = player.get_techniques_list()
        if slot_or_name in techniques_list:
            techniques_list.remove(slot_or_name)
            player.set_techniques_list(techniques_list)
            await self.db.update_player(player)
            return True, f"已卸下功法【{slot_or_name}】"

        return False, f"未找到装备：{slot_or_name}"
