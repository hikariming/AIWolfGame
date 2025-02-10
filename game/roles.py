"""
游戏角色定义

主要职责：
1. 定义角色类型枚举
2. 定义基础角色类
3. 实现具体角色类（狼人、村民）
"""

from enum import Enum
from typing import Optional, List
import logging

class RoleType(Enum):
    WEREWOLF = "werewolf"
    VILLAGER = "villager"

class BaseRole:
    def __init__(self, player_id: str, name: str, role_type: RoleType):
        self.player_id = player_id
        self.name = name
        self.role_type = role_type
        self.is_alive = True

    def is_wolf(self) -> bool:
        """判断是否是狼人"""
        return self.role_type == RoleType.WEREWOLF

class Werewolf(BaseRole):
    def __init__(self, player_id: str, name: str):
        super().__init__(player_id, name, RoleType.WEREWOLF)

class Villager(BaseRole):
    def __init__(self, player_id: str, name: str):
        super().__init__(player_id, name, RoleType.VILLAGER)
