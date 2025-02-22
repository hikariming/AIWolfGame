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
        """检查是否可以查验目标玩家"""
        return target_id not in self.checked_players

    def check_role(self, target_id: str) -> None:
        """记录查验过的玩家"""
        self.checked_players.add(target_id)

class Witch(BaseRole):
    def __init__(self, player_id: str, name: str):
        super().__init__(player_id, name, RoleType.WITCH)
        self.has_poison = True    # 毒药
        self.has_medicine = True  # 解药

    def can_save(self) -> bool:
        """检查是否可以使用解药"""
        return self.has_medicine

    def can_poison(self) -> bool:
        """检查是否可以使用毒药"""
        return self.has_poison

    def use_medicine(self) -> None:
        """使用解药"""
        self.has_medicine = False

    def use_poison(self) -> None:
        """使用毒药"""
        self.has_poison = False

class Hunter(BaseRole):
    def __init__(self, player_id: str, name: str):
        super().__init__(player_id, name, RoleType.HUNTER)
        self.can_shoot = True  # 是否可以开枪

    def can_use_gun(self) -> bool:
        """检查是否可以开枪"""
        return self.can_shoot and self.is_alive

    def use_gun(self) -> None:
        """使用开枪技能"""
        self.can_shoot = False
