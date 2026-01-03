# handlers/__init__.py

from .player_handler import PlayerHandler
from .misc_handler import MiscHandler
from .equipment_handler import EquipmentHandler
from .breakthrough_handler import BreakthroughHandler
from .pill_handler import PillHandler
from .shop_handler import ShopHandler
from .storage_ring_handler import StorageRingHandler
from .sect_handlers import SectHandlers
from .boss_handlers import BossHandlers
from .combat_handlers import CombatHandlers
from .ranking_handlers import RankingHandlers

from .rift_handlers import RiftHandlers
from .adventure_handlers import AdventureHandlers
from .alchemy_handlers import AlchemyHandlers
from .impart_handlers import ImpartHandlers
from .nickname_handler import NicknameHandler
from .bank_handlers import BankHandlers
from .bounty_handlers import BountyHandlers
from .impart_pk_handlers import ImpartPkHandlers
# Phase 4
from .blessed_land_handlers import BlessedLandHandlers
from .spirit_farm_handlers import SpiritFarmHandlers
from .dual_cultivation_handlers import DualCultivationHandlers
from .spirit_eye_handlers import SpiritEyeHandlers
# Phase 5: 沉浸式修仙系统
from .tribulation_handlers import TribulationHandlers
from .enlightenment_handlers import EnlightenmentHandlers
from .fortune_handlers import FortuneHandlers
from .inner_demon_handlers import InnerDemonHandlers
# Phase 6: 灵石互动
from .gold_interaction_handlers import GoldInteractionHandlers
# Phase 7: 仙缘红包
from .red_packet_handlers import RedPacketHandlers
# Phase 8: 通天塔
from .tower_handlers import TowerHandlers
# Phase 9: 社交互动
from .social_handlers import SocialHandlers
# Phase 10: 黑市
from .black_market_handler import BlackMarketHandler

__all__ = [
    "PlayerHandler",
    "MiscHandler",
    "EquipmentHandler",
    "BreakthroughHandler",
    "PillHandler",
    "ShopHandler",
    "StorageRingHandler",
    "SectHandlers",
    "BossHandlers",
    "CombatHandlers",
    "RankingHandlers",
    "RiftHandlers",
    "AdventureHandlers",
    "AlchemyHandlers",
    "ImpartHandlers",
    "NicknameHandler",
    "BankHandlers",
    "BountyHandlers",
    "ImpartPkHandlers",
    # Phase 4
    "BlessedLandHandlers",
    "SpiritFarmHandlers",
    "DualCultivationHandlers",
    "SpiritEyeHandlers",
    # Phase 5: 沉浸式修仙系统
    "TribulationHandlers",
    "EnlightenmentHandlers",
    "FortuneHandlers",
    "InnerDemonHandlers",
    # Phase 6: 灵石互动
    "GoldInteractionHandlers",
    # Phase 7: 仙缘红包
    "RedPacketHandlers",
    # Phase 8: 通天塔
    "TowerHandlers",
    # Phase 9: 社交互动
    "SocialHandlers",
    # Phase 10: 黑市
    "BlackMarketHandler",
]
