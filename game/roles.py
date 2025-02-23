"""
游戏角色定义

主要职责：
1. 定义角色类型枚举
2. 定义基础角色类
3. 实现具体角色类（狼人、村民、神职）
"""

from enum import Enum
from typing import Optional, List
import logging

class RoleType(Enum):
    WEREWOLF = "werewolf"
    VILLAGER = "villager"
    SEER = "seer"        # 预言家
    WITCH = "witch"      # 女巫
    HUNTER = "hunter"    # 猎人

class BaseRole:
    def __init__(self, player_id: str, name: str, role_type: RoleType):
        self.player_id = player_id
        self.name = name
        self.role_type = role_type
        self.is_alive = True
        self.used_skills = set()  # 记录已使用的技能
        self.logger = logging.getLogger(__name__)

    def is_wolf(self) -> bool:
        """判断是否是狼人"""
        return self.role_type == RoleType.WEREWOLF

    def is_god(self) -> bool:
        """判断是否是神职"""
        return self.role_type in [RoleType.SEER, RoleType.WITCH, RoleType.HUNTER]

class Werewolf(BaseRole):
    def __init__(self, player_id: str, name: str):
        super().__init__(player_id, name, RoleType.WEREWOLF)

class Villager(BaseRole):
    def __init__(self, player_id: str, name: str):
        super().__init__(player_id, name, RoleType.VILLAGER)

class Seer(BaseRole):
    def __init__(self, player_id: str, name: str):
        super().__init__(player_id, name, RoleType.SEER)
        self.checked_players = set()  # 记录已经查验过的玩家

    def can_check(self, target_id: str) -> bool:
        """检查是否可以查验目标玩家
        
        Args:
            target_id: 目标玩家ID
            
        Returns:
            bool: 是否可以查验
        """
        # 预言家每晚都可以查验一个人，但不能查验已经死亡的玩家
        # 也不建议查验同一个人（虽然规则上允许）
        if not self.is_alive:
            self.logger.debug(f"预言家已死亡，无法查验")
            return False
        if target_id in self.checked_players:
            self.logger.debug(f"玩家 {target_id} 已被查验过")
            return True  # 允许重复查验，但会给出警告
        return True

    def check_role(self, target_id: str) -> None:
        """记录查验过的玩家"""
        self.checked_players.add(target_id)
        self.logger.info(f"预言家查验了玩家 {target_id}")

class Witch(BaseRole):
    def __init__(self, player_id: str, name: str):
        super().__init__(player_id, name, RoleType.WITCH)
        self.has_poison = True    # 毒药
        self.has_medicine = True  # 解药
        self.used_medicine_this_round = False  # 记录本回合是否使用过解药

    def can_save(self, is_first_night: bool = False) -> bool:
        """检查是否可以使用解药
        
        Args:
            is_first_night: 是否是第一个晚上
            
        Returns:
            bool: 是否可以使用解药
        """
        if not self.is_alive:
            self.logger.debug("女巫已死亡，无法使用解药")
            return False
        if not self.has_medicine:
            self.logger.debug("解药已用完")
            return False
        if self.used_medicine_this_round:
            self.logger.debug("本回合已经使用过解药")
            return False
        return True

    def can_poison(self, is_first_night: bool = False) -> bool:
        """检查是否可以使用毒药
        
        Args:
            is_first_night: 是否是第一个晚上
            
        Returns:
            bool: 是否可以使用毒药
        """
        if not self.is_alive:
            self.logger.debug("女巫已死亡，无法使用毒药")
            return False
        if not self.has_poison:
            self.logger.debug("毒药已用完")
            return False
        if is_first_night:
            self.logger.debug("第一个晚上不建议使用毒药")
            return True  # 允许使用，但会给出警告
        return True

    def use_medicine(self) -> None:
        """使用解药"""
        self.has_medicine = False
        self.used_medicine_this_round = True
        self.logger.info("女巫使用了解药")

    def use_poison(self) -> None:
        """使用毒药"""
        self.has_poison = False
        self.logger.info("女巫使用了毒药")

    def reset_round(self) -> None:
        """重置回合状态"""
        self.used_medicine_this_round = False

class Hunter(BaseRole):
    def __init__(self, player_id: str, name: str):
        super().__init__(player_id, name, RoleType.HUNTER)
        self.can_shoot = True  # 是否可以开枪
        self.death_confirmed = False  # 是否确认死亡（被投票/被毒/被狼人杀）

    def can_use_gun(self) -> bool:
        """检查是否可以开枪
        
        Returns:
            bool: 是否可以开枪
        """
        if not self.death_confirmed:
            self.logger.debug("猎人未确认死亡，不能开枪")
            return False
        if not self.can_shoot:
            self.logger.debug("猎人已经开过枪了")
            return False
        return True

    def confirm_death(self) -> None:
        """确认死亡状态"""
        self.death_confirmed = True
        self.logger.info("猎人死亡已确认")

    def use_gun(self) -> None:
        """使用开枪技能"""
        if self.can_use_gun():
            self.can_shoot = False
            self.logger.info("猎人开枪了")
        else:
            self.logger.warning("猎人无法开枪")
