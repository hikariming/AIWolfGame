"""
AI 玩家系统

主要功能：
1. 统一的 AI 代理接口
2. 区分狼人、神职和村民阵营的代理
3. 维护对话历史和游戏状态记忆
4. 统一使用 OpenAI API 进行调用
"""

from typing import Optional, Dict, Any, List
from openai import OpenAI
import logging
import re
from .roles import BaseRole, RoleType
import random

class Memory:
    def __init__(self):
        self.conversations: List[Dict] = []  # 所有对话记录
        self.game_results: List[Dict] = []   # 每轮游戏结果
        self.current_round_discussions: List[Dict] = []  # 当前回合的讨论记录

    def add_conversation(self, conversation: Dict):
        """添加对话记录
        
        Args:
            conversation: 包含回合、阶段、说话者和内容的字典
        """
        self.conversations.append(conversation)
        if conversation.get("phase") == "discussion":
            self.current_round_discussions.append(conversation)

    def add_game_result(self, result: Dict):
        self.game_results.append(result)

    def get_current_round_discussions(self) -> List[Dict]:
        """获取当前回合的所有讨论"""
        return self.current_round_discussions

    def clear_current_round(self):
        """清空当前回合的讨论记录"""
        self.current_round_discussions = []

    def get_recent_conversations(self, count: int = 5) -> List[Dict]:
        """获取最近的几条对话记录，并格式化为易读的形式"""
        recent = self.conversations[-count:] if self.conversations else []
        formatted = []
        for conv in recent:
            if conv.get("phase") == "discussion":
                formatted.append(f"{conv.get('speaker', '未知')}说：{conv.get('content', '')}")
        return formatted

    def get_all_conversations(self) -> str:
        """获取所有对话记录的格式化字符串"""
        if not self.conversations:
            return "暂无历史记录"
            
        formatted = []
        current_round = None
        
        for conv in self.conversations:
            # 如果是新的回合，添加回合标记
            if current_round != conv.get("round"):
                current_round = conv.get("round")
                formatted.append(f"\n=== 第 {current_round} 回合 ===\n")
            
            if conv.get("phase") == "discussion":
                formatted.append(f"{conv.get('speaker', '未知')}说：{conv.get('content', '')}")
            elif conv.get("phase") == "vote":
                formatted.append(f"{conv.get('speaker', '未知')}投票给了{conv.get('target', '未知')}，理由：{conv.get('content', '')}")
            elif conv.get("phase") == "death":
                formatted.append(f"{conv.get('speaker', '未知')}的遗言：{conv.get('content', '')}")
        
        return "\n".join(formatted)

class BaseAIAgent:
    def __init__(self, config: Dict[str, Any], role: BaseRole):
        self.config = config
        self.role = role
        self.logger = logging.getLogger(__name__)
        self.memory = Memory()
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config.get("baseurl")
        )

    def ask_ai(self, prompt: str, system_prompt: str = None) -> str:
        """统一的 AI 调用接口"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"AI 调用失败: {str(e)}")
            return "【皱眉思考】经过深思熟虑，我认为villager1比较可疑。选择villager1"

    def _extract_target(self, response: str) -> Optional[str]:
        """从 AI 响应中提取目标玩家 ID
        
        Args:
            response: AI的完整响应文本
        
        Returns:
            str: 目标玩家ID，如果没有找到则返回None
        """
        try:
            # 使用正则表达式匹配以下格式：
            # 1. 选择[玩家ID]
            # 2. 选择玩家ID
            # 3. 选择 玩家ID
            # 4. 选择：玩家ID
            patterns = [
                r'选择\[([^\]]+)\]',  # 匹配 选择[wolf1] 或 选择[villager1]
                r'选择\s*(\w+\d*)',   # 匹配 选择wolf1 或 选择 villager1
                r'选择[：:]\s*(\w+\d*)'  # 匹配 选择：wolf1 或 选择:villager1
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response)
                if matches:
                    # 提取玩家ID，去除可能的额外空格和括号
                    target = matches[-1].strip('()[]').strip()
                    # 验证是否是有效的玩家ID格式
                    if re.match(r'^(wolf|villager)\d+$', target):
                        return target
            
            # 如果上面的模式都没匹配到，尝试查找带括号的玩家ID
            id_pattern = r'\((\w+\d+)\)'
            matches = re.findall(id_pattern, response)
            if matches:
                target = matches[-1]
                if re.match(r'^(wolf|villager)\d+$', target):
                    return target
                
            self.logger.warning(f"无法从响应中提取有效的目标ID: {response}")
            return None
        
        except Exception as e:
            self.logger.error(f"提取目标ID时出错: {str(e)}")
            return None

    def discuss(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """讨论阶段"""
        prompt = self._generate_discussion_prompt(game_state)
        response = self.ask_ai(prompt, self._get_discussion_prompt())
        
        # 记录讨论，包含说话者信息
        self.memory.add_conversation({
            "round": game_state["current_round"],
            "phase": "discussion",
            "speaker": self.role.name,
            "content": response
        })
        
        # 更新游戏状态中的讨论记录
        if "discussions" not in game_state:
            game_state["discussions"] = []
        game_state["discussions"].append({
            "speaker": self.role.name,
            "content": response
        })
        
        return {
            "type": "discuss",
            "content": response
        }

    def vote(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """投票决定
        
        Args:
            game_state: 游戏状态
            
        Returns:
            Dict 包含:
                - target: 投票目标ID
                - reason: 投票理由
        """
        prompt = self._generate_vote_prompt(game_state)
        response = self.ask_ai(prompt, self._get_werewolf_vote_prompt())
        
        # 从响应中提取目标ID和理由
        target = self._extract_target(response)
        
        # 添加防止自投的逻辑
        if target == self.role.name:
            self.logger.warning(f"{self.role.name} 试图投票给自己，重新选择一个随机目标")
            alive_players = [pid for pid, info in game_state['players'].items() 
                            if info['is_alive'] and pid != self.role.name]
            if alive_players:
                target = random.choice(alive_players)
        
        return {
            "target": target,
            "reason": response
        }

    def _generate_action_prompt(self) -> str:
        """生成动作和神色的提示词"""
        return """
        请在发言时加入动作和表情描写，要求：
        1. 用【】包裹动作和表情
        2. 描写要生动形象，符合角色身份
        3. 至少20个字的动作描写
        4. 动作要自然地融入发言中
        5. 表现出说话时的情绪变化
        """

    def _format_discussions(self, discussions: List[Dict]) -> str:
        """格式化讨论记录"""
        if not discussions:
            return "暂无讨论记录"
        
        formatted = []
        for disc in discussions:
            formatted.append(f"{disc['speaker']} 说：{disc['content']}")
        return "\n".join(formatted)

    def _get_discussion_prompt(self) -> str:
        """获取讨论的系统提示词"""
        return """你正在参与一场游戏讨论。请根据当前的游戏状态和讨论记录，给出合理的分析和判断。"""

    def _get_werewolf_vote_prompt(self) -> str:
        return """你是一个狼人玩家，正在根据讨论情况投票。
        要考虑：
        1. 分析局势，但要站在好人的角度思考
        2. 适当怀疑某些玩家，但不要过分指向好人
        3. 注意不要暴露自己和队友的身份
        4. 用"选择[玩家ID]"格式说明投票决定
        """

    def last_words(self, game_state: Dict[str, Any]) -> str:
        """处理玩家的遗言"""
        prompt = f"""
        当前游戏状态:
        - 回合: {game_state['current_round']}
        - 你的身份: {self.role.role_type.value} {self.role.name}
        - 你即将死亡，这是你最后的遗言。
        
        请说出你的遗言：
        1. 可以揭示自己的真实身份
        2. 可以给出对局势的分析
        3. 可以给存活的玩家一些建议
        4. 发言要符合角色身份
        5. 加入适当的动作描写
        """
        
        response = self.ask_ai(prompt, self._get_last_words_prompt())
        return response

    def _get_last_words_prompt(self) -> str:
        """获取遗言的系统提示词"""
        return """你正在发表临终遗言。
        要求：
        1. 符合角色身份特征
        2. 表达真挚的情感
        3. 可以给出重要的信息
        4. 为存活的玩家指明方向
        """

    def _generate_discussion_prompt(self, game_state: Dict[str, Any]) -> str:
        """生成讨论提示词，包含所有历史发言"""
        base_prompt = f"""
        {self._generate_action_prompt()}
        
        当前游戏状态:
        - 回合: {game_state['current_round']}
        - 存活玩家: {[f"{info['name']}({pid})" for pid, info in game_state['players'].items() if info['is_alive']]}
        - 你的身份: {self.role.role_type.value} {self.role.name}
        
        当前回合的讨论记录：
        {self._format_discussions(game_state.get('discussions', []))}
        
        历史记录：
        {self.memory.get_all_conversations()}
        """
        return base_prompt

    def _generate_vote_prompt(self, game_state: Dict[str, Any]) -> str:
        return f"""
        当前游戏状态:
        - 回合: {game_state['current_round']}
        - 存活玩家: {[f"{info['name']}({pid})" for pid, info in game_state['players'].items() 
                    if info['is_alive'] and pid != self.role.name]}
        - 你的身份: {self.role.role_type.value}
        
        完整对话记录：
        {self.memory.get_all_conversations()}
        
        请详细说明你要投票给谁，以及投票的理由。注意：不能投票给自己！
        
        要求：
        1. 分析局势，给出合理的投票理由
        2. 考虑其他玩家的发言和行为
        3. 必须以"选择[玩家ID]"的格式来明确指出你的投票目标
        4. 玩家ID必须是完整的格式，如wolf1、villager1等
        5. 不能选择自己作为投票目标
        """

class WerewolfAgent(BaseAIAgent):
    def __init__(self, config: Dict[str, Any], role: BaseRole):
        super().__init__(config, role)
        self.team_members: List[str] = []  # 狼队友列表

    def discuss(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """狼人讨论"""
        prompt = self._generate_discussion_prompt(game_state)
        response = self.ask_ai(prompt, self._get_werewolf_discussion_prompt())
        
        # 记录讨论
        self.memory.add_conversation({
            "round": game_state["current_round"],
            "phase": "discussion",
            "content": response
        })
        
        # 尝试解析JSON响应
        try:
            if game_state["phase"] == "night":
                # 夜间杀人讨论
                return {
                    "type": "kill",
                    "content": response,
                    "target": self._extract_target(response)
                }
            else:
                # 白天正常发言
                return {
                    "type": "discuss",
                    "content": response
                }
        except Exception as e:
            self.logger.error(f"解析响应失败: {str(e)}")
            return {
                "type": "error",
                "content": response,
                "target": "villager1"
            }

    def vote(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """根据讨论做出投票决定"""
        prompt = self._generate_vote_prompt(game_state)
        response = self.ask_ai(prompt, self._get_werewolf_vote_prompt())
        
        # 从响应中提取目标ID和理由
        target = self._extract_target(response)
        
        return {
            "target": target,
            "reason": response
        }

    def _generate_discussion_prompt(self, game_state: Dict[str, Any]) -> str:
        """重写狼人的讨论提示词，加入队友信息"""
        base_prompt = f"""
        {self._generate_action_prompt()}
        
        当前游戏状态:
        - 回合: {game_state['current_round']}
        - 存活玩家: {[f"{info['name']}({pid})" for pid, info in game_state['players'].items() if info['is_alive']]}
        - 你的身份: 狼人 {self.role.name}
        - 你的队友: {[game_state['players'][pid]['name'] for pid in self.team_members]}
        - 历史记录: {self.memory.get_recent_conversations()}
        """
        
        if game_state["phase"] == "night":
            return base_prompt + """
            作为狼人，请讨论今晚要杀死谁：
            1. 分析每个玩家的威胁程度，但不要说出具体角色
            2. 考虑每个人的行为特征
            3. 给出详细的理由
            4. 发言必须超过20个字
            5. 最后用"选择[玩家ID]"格式说明你的决定
            6. 不要在发言中透露你已经知道某个玩家的具体身份
            """
        else:
            return base_prompt + """
            请以好人的身份发表你的看法：
            1. 分析每个玩家的行为和发言
            2. 表达你对局势的判断
            3. 适当表达怀疑，但不要暴露自己
            4. 发言必须超过20个字
            5. 尝试引导方向，保护队友
            6. 不要在发言中透露你已经知道某个玩家的具体身份
            """

    def _get_werewolf_discussion_prompt(self) -> str:
        return """你是一个狼人玩家，需要决定今晚要杀死谁。
        要考虑：
        1. 分析每个玩家的威胁程度，但不要在发言中直接说出你认为他们是什么角色
        2. 避免暴露自己和队友的身份
        3. 分析其他玩家的行为模式
        4. 与队友的意见保持协调
        5. 不要在发言中透露你已经知道某个玩家的具体身份
        6. 用含蓄的方式表达你的判断，比如"这个人比较危险"而不是"他是预言家"
        请给出分析和最终决定。
        """

    def _get_werewolf_vote_prompt(self) -> str:
        return """你是一个狼人玩家，正在根据讨论情况投票。
        要考虑：
        1. 分析局势，但要站在好人的角度思考
        2. 适当怀疑某些玩家，但不要过分指向好人
        3. 注意不要暴露自己和队友的身份
        4. 用"选择[玩家ID]"格式说明投票决定
        """

class VillagerAgent(BaseAIAgent):
    def discuss(self, game_state: Dict[str, Any]) -> str:
        """村民讨论发言"""
        prompt = self._generate_discussion_prompt(game_state)
        response = self.ask_ai(prompt, self._get_villager_discussion_prompt())
        
        # 记录讨论
        self.memory.add_conversation({
            "round": game_state["current_round"],
            "phase": "discussion",
            "content": response
        })
        
        return {
            "type": "discuss",
            "content": response
        }

    def vote(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """村民根据讨论做出投票决定"""
        prompt = self._generate_vote_prompt(game_state)
        response = self.ask_ai(prompt, self._get_villager_vote_prompt())
        target = self._extract_target(response)
        return {
            "target": target,
            "reason": response
        }

    def _get_villager_discussion_prompt(self) -> str:
        """获取村民的系统提示词"""
        return """你是一个村民玩家，需要找出狼人。
        要考虑：
        1. 仔细分析每个玩家的发言和行为
        2. 寻找可疑的矛盾点
        3. 与其他村民合作找出狼人
        4. 保持理性和逻辑性
        请给出你的分析和判断。
        """

    def _get_villager_vote_prompt(self) -> str:
        """获取村民投票的系统提示词"""
        return """你是一个村民玩家，需要投票选出最可疑的狼人。
        要考虑：
        1. 根据之前的讨论做出判断
        2. 给出合理的投票理由
        3. 避免被狼人误导
        4. 用"选择[玩家ID]"格式说明投票决定
        """

class SeerAgent(BaseAIAgent):
    def __init__(self, config: Dict[str, Any], role: BaseRole):
        super().__init__(config, role)
        self.checked_results = {}  # 记录查验结果

    def check_player(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """夜晚查验玩家身份"""
        prompt = self._generate_check_prompt(game_state)
        response = self.ask_ai(prompt, self._get_seer_check_prompt())
        
        target = self._extract_target(response)
        if target:
            self.checked_results[target] = game_state["players"][target]["role"]
            
        return {
            "type": "check",
            "target": target,
            "reason": response
        }

    def _get_seer_check_prompt(self) -> str:
        return """你是预言家，需要选择一个玩家查验身份。
        要考虑：
        1. 分析可疑玩家的行为
        2. 避免重复查验同一个人
        3. 优先查验最可疑的对象
        4. 用"选择[玩家ID]"格式说明查验目标
        """

    def _generate_check_prompt(self, game_state: Dict[str, Any]) -> str:
        return f"""
        当前游戏状态:
        - 回合: {game_state['current_round']}
        - 存活玩家: {[f"{info['name']}({pid})" for pid, info in game_state['players'].items() if info['is_alive']]}
        - 已查验玩家: {list(self.checked_results.keys())}
        
        请选择今晚要查验的玩家：
        1. 分析每个玩家的行为
        2. 考虑历史发言内容
        3. 给出详细的理由
        4. 用"选择[玩家ID]"格式说明查验目标
        """

class WitchAgent(BaseAIAgent):
    def __init__(self, config: Dict[str, Any], role: BaseRole):
        super().__init__(config, role)

    def use_potion(self, game_state: Dict[str, Any], victim_id: Optional[str] = None) -> Dict[str, Any]:
        """决定使用解药或毒药"""
        prompt = self._generate_potion_prompt(game_state, victim_id)
        response = self.ask_ai(prompt, self._get_witch_prompt())
        
        # 解析决策
        if "使用解药" in response and victim_id:
            return {
                "type": "save",
                "target": victim_id,
                "reason": response
            }
        elif "使用毒药" in response:
            target = self._extract_target(response)
            if target:
                return {
                    "type": "poison",
                    "target": target,
                    "reason": response
                }
        
        return {
            "type": "skip",
            "reason": response
        }

    def _get_witch_prompt(self) -> str:
        return """你是女巫，需要决定是否使用药水。
        要考虑：
        1. 解药和毒药只能各使用一次
        2. 解药要慎重使用，考虑被害者身份
        3. 毒药要留到关键时刻
        4. 明确说明"使用解药"或"使用毒药 选择[玩家ID]"
        """

    def _generate_potion_prompt(self, game_state: Dict[str, Any], victim_id: Optional[str] = None) -> str:
        witch_role = self.role
        prompt = f"""
        当前游戏状态:
        - 回合: {game_state['current_round']}
        - 存活玩家: {[f"{info['name']}({pid})" for pid, info in game_state['players'].items() if info['is_alive']]}
        - 解药状态: {'可用' if witch_role.can_save() else '已用'}
        - 毒药状态: {'可用' if witch_role.can_poison() else '已用'}
        """
        
        if victim_id and witch_role.can_save():
            prompt += f"\n今晚的遇害者是：{game_state['players'][victim_id]['name']}({victim_id})"
        
        prompt += """
        请决定：
        1. 是否使用解药救人
        2. 是否使用毒药杀人
        3. 给出详细的理由
        4. 使用"使用解药"或"使用毒药 选择[玩家ID]"格式
        """
        return prompt

class HunterAgent(BaseAIAgent):
    def __init__(self, config: Dict[str, Any], role: BaseRole):
        super().__init__(config, role)

    def shoot(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """决定开枪打死谁"""
        prompt = self._generate_shoot_prompt(game_state)
        response = self.ask_ai(prompt, self._get_hunter_prompt())
        
        target = self._extract_target(response)
        return {
            "type": "shoot",
            "target": target,
            "reason": response
        }

    def _get_hunter_prompt(self) -> str:
        return """你是猎人，即将死亡，需要决定开枪打死谁。
        要考虑：
        1. 分析场上局势
        2. 选择最可能是狼人的目标
        3. 给出详细的理由
        4. 用"选择[玩家ID]"格式说明射击目标
        """

    def _generate_shoot_prompt(self, game_state: Dict[str, Any]) -> str:
        return f"""
        当前游戏状态:
        - 回合: {game_state['current_round']}
        - 存活玩家: {[f"{info['name']}({pid})" for pid, info in game_state['players'].items() if info['is_alive']]}
        - 历史记录: {self.memory.get_recent_conversations()}
        
        你即将死亡，请决定开枪打死谁：
        1. 分析每个玩家的行为
        2. 考虑历史发言内容
        3. 给出详细的理由
        4. 用"选择[玩家ID]"格式说明射击目标
        """

def create_ai_agent(config: Dict[str, Any], role: BaseRole) -> BaseAIAgent:
    """工厂函数：根据角色创建对应的 AI 代理"""
    if role.role_type == RoleType.WEREWOLF:
        return WerewolfAgent(config, role)
    elif role.role_type == RoleType.SEER:
        return SeerAgent(config, role)
    elif role.role_type == RoleType.WITCH:
        return WitchAgent(config, role)
    elif role.role_type == RoleType.HUNTER:
        return HunterAgent(config, role)
    else:
        return VillagerAgent(config, role)
