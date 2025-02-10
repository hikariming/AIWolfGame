"""
游戏通用工具函数集合

主要功能：
1. 配置文件处理
   - 读取 JSON 配置
   - 验证配置有效性
   - 合并默认配置

2. 游戏辅助功能
   - 随机角色分配
   - 计算投票结果
   - 游戏状态检查
   - 定时器实现

3. 与其他模块的交互：
   - 被 game_controller.py 调用使用工具函数
   - 被 ai_players.py 使用配置处理
   - 提供通用异常处理

函数列表：
def load_config()
def validate_config()
def assign_roles()
def calculate_votes()
def create_timer()
def handle_exceptions()
""" 