"""
游戏角色定义和能力实现

主要职责：
1. 角色基类
   - 定义通用角色属性
   - 实现基础行为（发言、投票等）

2. 具体角色实现
   - 狼人：夜晚杀人能力
   - 预言家：查验身份能力
   - 女巫：使用药水能力
   - 村民：基本行为

3. 与其他模块的交互：
   - 被 game_controller.py 调用使用角色能力
   - 与 ai_players.py 配合进行决策
   - 使用 config/role_config.json 的配置

类设计：
class BaseRole:
    def __init__()
    def speak()
    def vote()

class Werewolf(BaseRole):
    def kill()

class Seer(BaseRole):
    def check_identity()

class Witch(BaseRole):
    def use_potion()

class Villager(BaseRole):
    # 基本村民实现
""" 