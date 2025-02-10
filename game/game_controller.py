"""
游戏主控制器，负责整个游戏流程的控制和状态管理

主要职责：
1. 游戏初始化
   - 加载配置文件
   - 初始化玩家和角色
   - 分配角色

2. 游戏流程控制
   - 管理游戏阶段（夜晚/白天）
   - 控制发言顺序
   - 处理投票环节
   - 判断游戏结束条件

3. 与其他模块的交互：
   - 调用 ai_players.py 中的 AI 玩家进行决策
   - 使用 roles.py 中定义的角色能力
   - 通过 utils/logger.py 记录游戏过程
   - 通过 utils/game_utils.py 使用辅助功能

类设计：
class GameController:
    def __init__(self)
    def initialize_game()
    def start_game()
    def night_phase()
    def day_phase()
    def voting_phase()
    def check_game_over()
    def announce_winner()
""" 