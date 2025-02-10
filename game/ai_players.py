"""
AI 玩家系统

主要功能：
1. 统一的 AI 代理接口
2. 区分狼人和人类阵营的代理
3. 维护对话历史和游戏状态记忆
4. 统一使用 OpenAI API 进行调用
"""

from typing import Optional, Dict, Any, List
import openai
import logging
import re
from .roles import BaseRole

class Memory:
    def __init__(self):
        self.conversations: List[Dict] = []  # 所有对话记录
        self.game_results: List[Dict] = []   # 每轮游戏结果

    def add_conversation(self, conversation: Dict):
        self.conversations.append(conversation)

    def add_game_result(self, result: Dict):
        self.game_results.append(result)

    def get_recent_conversations(self, count: int = 5) -> List[Dict]:
        """获取最近的几条对话记录"""
        return self.conversations[-count:] if self.conversations else []

class BaseAIAgent:
    def __init__(self, config: Dict[str, Any], role: BaseRole):
        self.config = config
        self.role = role
        self.logger = logging.getLogger(__name__)
        self.memory = Memory()
        openai.api_key = config["api_key"]
        self.base_url = config.get("baseurl")

    async def ask_ai(self, prompt: str, system_prompt: str = None) -> str:
        """统一的 AI 调用接口"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await openai.ChatCompletion.acreate(
                model=self.config["model"],
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"AI 调用失败: {str(e)}")
            return ""

    def _extract_target(self, response: str) -> str:
        """从 AI 响应中提取目标玩家 ID"""
        # 使用正则表达式匹配玩家 ID
        match = re.search(r'选择(\w+)', response)
        if match:
            return match.group(1)
        return ""

    def make_decision(self, game_state: Dict[str, Any]) -> str:
        """基础决策方法"""
        raise NotImplementedError

class WerewolfAgent(BaseAIAgent):
    def __init__(self, config: Dict[str, Any], role: BaseRole):
        super().__init__(config, role)
        self.team_members: List[str] = []  # 狼队友列表

    def discuss_kill(self, game_state: Dict[str, Any]) -> str:
        """狼人夜间讨论决定杀人目标"""
        prompt = self._generate_kill_prompt(game_state)
        response = self.ask_ai(prompt, self._get_werewolf_system_prompt())
        
        # 记录讨论
        self.memory.add_conversation({
            "round": game_state["current_round"],
            "phase": "night",
            "content": response
        })
        
        return self._extract_target(response)

    def discuss_vote(self, game_state: Dict[str, Any]) -> str:
        """狼人白天讨论投票"""
        prompt = self._generate_vote_prompt(game_state)
        response = self.ask_ai(prompt, self._get_werewolf_day_system_prompt())
        
        # 记录讨论
        self.memory.add_conversation({
            "round": game_state["current_round"],
            "phase": "day",
            "content": response
        })
        
        return self._extract_target(response)

    def _generate_kill_prompt(self, game_state: Dict[str, Any]) -> str:
        alive_players = [p for p, s in game_state["players"].items() 
                        if s["is_alive"] and p != self.role.player_id]
        recent_history = self.memory.get_recent_conversations()
        
        return f"""
        当前游戏状态:
        - 回合: {game_state['current_round']}
        - 存活玩家: {alive_players}
        - 你的身份: 狼人
        - 你的队友: {self.team_members}
        - 最近的发言和事件: {recent_history}
        
        作为狼人，你知道：
        1. {self.role.name}（你自己）是狼人
        2. {', '.join([game_state['players'][pid]['name'] for pid in self.team_members])} 是你的狼人队友
        
        请分析形势并选择一个要杀死的目标。
        要求：
        1. 分析每个非狼人玩家的威胁程度
        2. 考虑对方可能的特殊角色（如预言家）
        3. 给出选择的具体理由
        4. 用"选择[玩家ID]"格式说明最终决定
        """

    def _generate_vote_prompt(self, game_state: Dict[str, Any]) -> str:
        alive_players = [p for p, s in game_state["players"].items() 
                        if s["is_alive"] and p != self.role.player_id]
        recent_history = self.memory.get_recent_conversations()
        
        return f"""
        当前游戏状态:
        - 回合: {game_state['current_round']}
        - 存活玩家: {alive_players}
        - 你的身份: 狼人
        - 你的队友: {self.team_members}
        - 最近的发言和事件: {recent_history}
        
        作为狼人，你需要在白天伪装成好人发言。
        要求：
        1. 分析局势，但要站在好人的角度思考
        2. 适当怀疑某些玩家，但不要过分指向好人
        3. 注意不要暴露自己和队友的身份
        4. 用"选择[玩家ID]"格式说明投票决定
        """

    def _get_werewolf_system_prompt(self) -> str:
        return """你是一个狼人玩家，正在和队友商量今晚要杀死谁。
        要考虑：
        1. 优先杀死对狼人威胁大的玩家
        2. 避免暴露自己和队友的身份
        3. 分析其他玩家的行为模式
        4. 与队友的意见保持协调
        请给出分析和最终决定。
        """

    def _get_werewolf_day_system_prompt(self) -> str:
        return """你是一个狼人玩家，正在白天伪装成好人发言。
        要考虑：
        1. 表现得像一个认真找狼人的好人
        2. 适当怀疑和引导方向，但不要太明显
        3. 在关键时刻保护自己和队友
        4. 注意前后发言的一致性
        请给出合理的分析和投票决定。
        """

class VillagerAgent(BaseAIAgent):
    def discuss_vote(self, game_state: Dict[str, Any]) -> str:
        """村民讨论投票"""
        prompt = self._generate_vote_prompt(game_state)
        response = self.ask_ai(prompt, self._get_villager_system_prompt())
        
        # 记录讨论
        self.memory.add_conversation({
            "round": game_state["current_round"],
            "phase": "day",
            "content": response
        })
        
        return self._extract_target(response)

    def _generate_vote_prompt(self, game_state: Dict[str, Any]) -> str:
        alive_players = [p for p, s in game_state["players"].items() 
                        if s["is_alive"] and p != self.role.player_id]
        recent_history = self.memory.get_recent_conversations()
        
        return f"""
        当前游戏状态:
        - 回合: {game_state['current_round']}
        - 存活玩家: {alive_players}
        - 历史记录: {recent_history}
        
        请分析局势并决定要投票给谁。
        要求：
        1. 分析每个玩家的发言
        2. 找出可疑的行为
        3. 给出推理过程
        4. 用"选择[玩家ID]"格式说明最终决定
        """

    def _get_villager_system_prompt(self) -> str:
        return """你是一个村民阵营的玩家，需要找出狼人。
        要考虑：
        1. 分析其他玩家的发言
        2. 注意前后矛盾的地方
        3. 找出可疑的行为模式
        请给出分析和投票决定。
        """

def create_ai_agent(config: Dict[str, Any], role: BaseRole) -> BaseAIAgent:
    """工厂函数：根据角色创建对应的 AI 代理"""
    if role.role_type == RoleType.WEREWOLF:
        return WerewolfAgent(config, role)
    else:
        return VillagerAgent(config, role)
```