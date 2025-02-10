"""
AI 玩家的基类和具体实现

主要职责：
1. AI 玩家基类
   - 定义 AI 玩家通用接口
   - 处理与 AI API 的通信
   - 管理提示词模板

2. 具体 AI 实现
   - 对接不同的 AI 模型（GPT-4, Claude, Local LLama 等）
   - 处理 API 响应
   - 实现重试机制

3. 与其他模块的交互：
   - 被 game_controller.py 调用进行决策
   - 使用 roles.py 中的角色信息
   - 通过 utils/logger.py 记录 AI 响应
   - 使用 config/ai_config.json 的配置

类设计：
class BaseAIPlayer:
    def __init__()
    def make_decision()
    def generate_speech()
    def handle_api_call()

class GPT4Player(BaseAIPlayer):
    # GPT-4 特定实现

class ClaudePlayer(BaseAIPlayer):
    # Claude 特定实现

class LocalLLamaPlayer(BaseAIPlayer):
    # Local LLama 特定实现
""" 