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
from datetime import datetime

class Memory:
    def __init__(self):
        self.conversations: List[Dict] = []  # 所有对话记录
        self.game_results: List[Dict] = []   # 每轮游戏结果
        self.current_round_discussions: List[Dict] = []  # 当前回合的讨论记录
        self.trust_ratings: Dict[str, List[Dict]] = {}  # 添加信任评分记录
        self.vote_history: List[Dict] = []  # 添加投票历史记录

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
    
    def add_trust_rating(self, rater_id: str, ratings: Dict[str, int], round_num: int):
        """添加信任评分
        
        Args:
            rater_id: 评分者ID
            ratings: 包含被评分者ID和评分(0-10)的字典
            round_num: 游戏轮次
        """
        if rater_id not in self.trust_ratings:
            self.trust_ratings[rater_id] = []
            
        timestamp = datetime.now().isoformat()
        for target_id, rating in ratings.items():
            self.trust_ratings[rater_id].append({
                "target": target_id,
                "rating": rating,
                "round": round_num,
                "timestamp": timestamp
            })
    
    def add_vote(self, voter_id: str, target_id: str, reason: str, round_num: int):
        """添加投票记录
        
        Args:
            voter_id: 投票者ID
            target_id: 被投票者ID
            reason: 投票理由
            round_num: 游戏轮次
        """
        self.vote_history.append({
            "voter": voter_id,
            "target": target_id,
            "reason": reason,
            "round": round_num,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_trust_ratings_for_round(self, round_num: int) -> Dict[str, Dict[str, int]]:
        """获取指定轮次所有玩家的信任评分
        
        Args:
            round_num: 游戏轮次
            
        Returns:
            Dict: 评分者ID -> {被评分者ID -> 评分}
        """
        result = {}
        for rater_id, ratings in self.trust_ratings.items():
            round_ratings = {}
            for rating in ratings:
                if rating["round"] == round_num:
                    round_ratings[rating["target"]] = rating["rating"]
            if round_ratings:
                result[rater_id] = round_ratings
        return result
    
    def get_vote_history_for_round(self, round_num: int) -> List[Dict]:
        """获取指定轮次的投票历史
        
        Args:
            round_num: 游戏轮次
            
        Returns:
            List[Dict]: 该轮次的投票记录列表
        """
        return [vote for vote in self.vote_history if vote["round"] == round_num]

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
                messages=messages
                                        )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"AI 调用失败: {str(e)}")
            return "【皱眉思考】经过深思熟虑，我认为player6比较可疑。选择player6"

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
            # 2. 选择 玩家ID
            # 3. 选择：玩家ID
            # 4. (玩家ID)
            # 5. 玩家ID(xxx)
            # 6. 我选择 玩家ID
            # 7. 投票给 玩家ID
            # 8. 怀疑 玩家ID
            patterns = [
                r'选择\[([^\]]+)\]',             # 匹配 选择[player1] 
                r'选择[：:]\s*(\w+\d*)',          # 匹配 选择：player1
                r'选择\s+(\w+\d*)',              # 匹配 选择 player1
                r'我[的]?选择[是为]?\s*[：:"]?\s*(\w+\d*)',  # 匹配 我选择是player1
                r'投票(给|选择|选)\s*[：:"]?\s*(\w+\d*)',   # 匹配 投票给player1
                r'[我认为]*(\w+\d+)[最非常]*(可疑|是狼人|有问题)',  # 匹配 player1最可疑
                r'[决定|准备]*(投|投票|票)[给向](\w+\d+)',  # 匹配 投给player1
                r'\((\w+\d*)\)',                 # 匹配 (player1)
                r'([a-zA-Z]+\d+)\s*\(',          # 匹配 player1(
                r'.*\b(player\d+)\b.*',          # 最宽松匹配，尝试找到任何player+数字
            ]
            
            # 首先尝试专用格式
            for i, pattern in enumerate(patterns):
                # 投票给player1 特殊处理
                if i == 4:  # 第5个模式需要特殊处理第二个捕获组
                    matches = re.findall(pattern, response)
                    if matches:
                        for match in matches:
                            if isinstance(match, tuple) and len(match) > 1:
                                target = match[1].strip()
                                if re.match(r'^player\d+$', target):
                                    return target
                else:
                    matches = re.findall(pattern, response)
                    if matches:
                        # 提取玩家ID，去除可能的额外空格和括号
                        target = matches[-1].strip('()[]"\'：: ').strip()
                        # 验证是否是有效的玩家ID格式
                        if re.match(r'^player\d+$', target):
                            return target
            
            # 如果上面的模式都没匹配到，尝试简单提取任何player+数字
            all_player_ids = re.findall(r'player\d+', response)
            if all_player_ids:
                return all_player_ids[-1]  # 返回最后一个匹配到的ID
            
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
        
        # 记录投票
        if target:
            self.memory.add_vote(self.role.player_id, target, response, game_state["current_round"])
        
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
        
        请根据以上信息，作为{self.role.role_type.value}，发表你的看法：
        1. 分析其他玩家的行为和发言，找出可疑之处
        2. 给出你的推理过程和判断依据
        3. 表达对局势的看法
        4. 发言要超过100字
        5. 记得加入动作描写【】
        """
        return base_prompt

    def _generate_vote_prompt(self, game_state: Dict[str, Any]) -> str:
        return f"""
        当前游戏状态:
        - 回合: {game_state['current_round']}
        - 存活玩家: {[f"{info['name']}({pid})" for pid, info in game_state['players'].items() 
                    if info['is_alive'] and pid != self.role.name]}
        - 你的身份: {self.role.role_type.value} {self.role.name}
        
        完整对话记录：
        {self.memory.get_all_conversations()}
        
        请详细说明你要投票给谁，以及投票的理由。注意：不能投票给自己！
        
        要求：
        1. 分析局势，给出合理的投票理由
        2. 考虑其他玩家的发言和行为
        3. 使用"我选择[player数字]"或"选择[player数字]"这样的格式来明确指出你的投票目标
        4. player ID必须是完整的格式，如player1、player2等
        5. 不能选择自己作为投票目标
        6. 给出充分的理由，至少50字
        
        例如良好的投票格式：
        "经过分析，我认为player3的行为最为可疑，他在第二轮的发言中自相矛盾，而且...（分析原因）...因此我选择[player3]"
        """

    def evaluate_trust(self, game_state: Dict[str, Any]) -> Dict[str, int]:
        """评估对其他玩家的信任度
        
        Args:
            game_state: 当前游戏状态
            
        Returns:
            Dict[str, int]: 玩家ID -> 信任度评分 (0-10)
        """
        prompt = self._generate_trust_evaluation_prompt(game_state)
        response = self.ask_ai(prompt, self._get_trust_evaluation_prompt())
        
        # 尝试从响应中提取信任评分
        trust_ratings = self._extract_trust_ratings(response, game_state)
        
        # 记录信任评分
        self.memory.add_trust_rating(self.role.player_id, trust_ratings, game_state["current_round"])
        
        return trust_ratings
    
    def _extract_trust_ratings(self, response: str, game_state: Dict[str, Any]) -> Dict[str, int]:
        """从AI回复中提取信任评分
        
        Args:
            response: AI回复文本
            game_state: 当前游戏状态
            
        Returns:
            Dict[str, int]: 玩家ID -> 信任度评分 (0-10)
        """
        trust_ratings = {}
        
        # 获取所有存活的玩家(除了自己)
        alive_players = [pid for pid, info in game_state["players"].items() 
                        if info["is_alive"] and pid != self.role.player_id]
        
        if not alive_players:
            self.logger.warning("没有其他存活玩家可评分")
            return trust_ratings
            
        self.logger.debug(f"AI回复: {response}")
        self.logger.debug(f"存活玩家: {alive_players}")
        
        try:
            # 使用多个正则表达式模式匹配不同格式的信任评分
            patterns = [
                r'([a-zA-Z]+\d+)[\s\:：]*(\d+)',                  # player1: 7
                r'对[\s]*([a-zA-Z]+\d+)[\s\:：]*评分[\s\:：]*(\d+)',  # 对player1评分: 7
                r'([a-zA-Z]+\d+)[\s\:：]+\D*?(\d+)[\s/分]*',      # player1: 信任度 7分
                r'信任度[\s\:：]*([a-zA-Z]+\d+)[\s\:：]*(\d+)'     # 信任度player1: 7
            ]
            
            # 尝试所有模式
            all_matches = []
            for pattern in patterns:
                matches = re.findall(pattern, response)
                all_matches.extend(matches)
                
            # 如果找到匹配项，处理它们
            for pid, score in all_matches:
                pid = pid.strip()
                if pid in alive_players:
                    try:
                        score_int = int(score.strip())
                        # 确保分数在0-10范围内
                        if 0 <= score_int <= 10:
                            trust_ratings[pid] = score_int
                            self.logger.debug(f"找到评分: {pid} -> {score_int}")
                    except ValueError:
                        self.logger.warning(f"无法将 {score} 转换为有效的信任评分")
            
            # 如果没有找到任何评分，尝试逐行分析
            if not trust_ratings:
                self.logger.warning("使用正则表达式未找到信任评分，尝试逐行分析")
                
                # 将响应分成行
                lines = response.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    # 跳过空行
                    if not line:
                        continue
                        
                    # 查找包含player ID的行
                    for player_id in alive_players:
                        if player_id in line:
                            # 查找该行中的数字
                            numbers = re.findall(r'\b(\d+)\b', line)
                            if numbers:
                                for num in numbers:
                                    try:
                                        score_int = int(num)
                                        if 0 <= score_int <= 10:
                                            trust_ratings[player_id] = score_int
                                            self.logger.debug(f"从行分析中找到评分: {player_id} -> {score_int}")
                                            break
                                    except ValueError:
                                        continue
            
            # 如果仍然没有找到任何评分，为所有人随机生成
            if not trust_ratings:
                self.logger.warning("无法从响应中提取信任评分，随机生成")
                for pid in alive_players:
                    trust_ratings[pid] = random.randint(3, 8)  # 使用更中性的随机范围
                    self.logger.debug(f"随机生成评分: {pid} -> {trust_ratings[pid]}")
                    
        except Exception as e:
            self.logger.error(f"提取信任评分时出错: {str(e)}")
            # 出错时随机生成
            for pid in alive_players:
                trust_ratings[pid] = random.randint(3, 8)  # 使用更中性的随机范围
                
        # 记录最终结果
        self.logger.info(f"提取到的信任评分: {trust_ratings}")
        return trust_ratings
    
    def _generate_trust_evaluation_prompt(self, game_state: Dict[str, Any]) -> str:
        """生成评估其他玩家信任度的提示词
        
        Args:
            game_state: 当前游戏状态
            
        Returns:
            str: 提示词
        """
        # 生成存活玩家列表
        alive_players = []
        for pid, info in game_state['players'].items():
            if info['is_alive'] and pid != self.role.player_id:
                alive_players.append(f"{info['name']}({pid})")
        
        # 避免没有玩家可评分的情况
        if not alive_players:
            return "没有其他存活玩家可以评分。"
            
        prompt = f"""
        当前游戏状态:
        - 回合: {game_state["current_round"]}
        - 存活玩家: {alive_players}
        - 你的身份: {self.role.role_type.value} {self.role.name}
        
        历史记录:
        {self.memory.get_all_conversations()}
        
        请对每个存活的玩家进行信任度评估(除了你自己)，范围从0分(完全不信任)到10分(完全信任)。
        
        【评分格式要求】（非常重要，必须严格遵守）:
        1. 必须为每个玩家单独评分
        2. 严格使用"玩家ID: 评分"的格式，例如"player1: 7"
        3. 评分必须是0-10的整数
        4. 每个玩家单独一行
        5. 评分后可以添加简短解释
        
        请按照以下格式回答:
        
        player1: 8 - 因为他的发言逻辑清晰，投票一致性高
        player2: 3 - 因为他经常自相矛盾，行为可疑
        
        请对以下玩家进行评分:
        {chr(10).join(alive_players)}
        """
        return prompt
    
    def _get_trust_evaluation_prompt(self) -> str:
        """获取信任评估的系统提示词"""
        return """你正在评估游戏中其他玩家的可信度。你必须严格按照要求的格式输出信任评分。
        
        评分考虑因素:
        1. 发言的一致性和逻辑性
        2. 投票行为是否可疑
        3. 与你的判断是否一致
        4. 是否有欺骗或隐瞒的迹象
        
        【格式要求】:
        1. 每个玩家必须使用"playerX: Y"格式评分，其中X是玩家ID，Y是0-10的整数评分
        2. 每个玩家单独一行
        3. 评分后可以简短解释原因，但格式必须保持
        4. 不要添加任何额外的格式或修饰
        
        例如:
        player1: 8 - 他的发言很有逻辑
        player2: 3 - 他的行为很可疑
        
        注意: 所有评分必须严格遵循上述格式，否则系统将无法正确解析你的评分。
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

    def _generate_discussion_prompt(self, game_state: Dict[str, Any]) -> str:
        base_prompt = super()._generate_discussion_prompt(game_state)
        base_prompt += "\n\n你是一个普通村民，没有特殊技能。你的目标是找出并投票处决狼人。"
        return base_prompt

    def _generate_vote_prompt(self, game_state: Dict[str, Any]) -> str:
        base_prompt = super()._generate_vote_prompt(game_state)
        base_prompt += "\n\n你是一个普通村民，没有特殊技能。请根据之前的讨论，投票选择你认为最可能是狼人的玩家。"
        return base_prompt

class SeerAgent(BaseAIAgent):
    def __init__(self, config: Dict[str, Any], role: BaseRole):
        super().__init__(config, role)
        self.role: Seer = role  # 类型提示

    def _generate_discussion_prompt(self, game_state: Dict[str, Any]) -> str:
        base_prompt = super()._generate_discussion_prompt(game_state)
        
        # 添加查验历史
        check_history = []
        for target_id, is_wolf in self.role.checked_players.items():
            if target_id in game_state["players"]:
                target_name = game_state["players"][target_id]["name"]
                result = "狼人" if is_wolf else "好人"
                check_history.append(f"- {target_name}: {result}")
        
        if check_history:
            base_prompt += "\n\n你的查验历史："
            base_prompt += "\n" + "\n".join(check_history)
        
        return base_prompt

    def _generate_vote_prompt(self, game_state: Dict[str, Any]) -> str:
        base_prompt = super()._generate_vote_prompt(game_state)
        
        # 添加查验历史到投票提示词
        check_history = []
        for target_id, is_wolf in self.role.checked_players.items():
            if target_id in game_state["players"]:
                target_name = game_state["players"][target_id]["name"]
                result = "狼人" if is_wolf else "好人"
                check_history.append(f"- {target_name}: {result}")
        
        if check_history:
            base_prompt += "\n\n你的查验历史："
            base_prompt += "\n" + "\n".join(check_history)
        
        return base_prompt

    def check_player(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """选择要查验的玩家
        
        Returns:
            Dict: 包含查验目标的字典
            {
                "type": "check",
                "target": target_id
            }
        """
        # 生成查验提示词
        prompt = self._generate_check_prompt(game_state)
        
        # 获取AI回复
        response = self.ask_ai(prompt, self._get_seer_check_prompt())
        
        # 从响应中提取目标ID
        target_id = self._extract_target(response)
        
        return {
            "type": "check",
            "target": target_id
        }

    def _get_seer_check_prompt(self) -> str:
        """获取预言家查验的系统提示词"""
        return """你是预言家，需要选择一个玩家进行查验。
        要考虑：
        1. 优先查验可疑的玩家
        2. 避免重复查验同一个玩家
        3. 给出合理的查验理由
        4. 用"选择[玩家ID]"格式说明查验目标
        """

    def _generate_check_prompt(self, game_state: Dict[str, Any]) -> str:
        """生成查验提示词"""
        alive_players = [
            (pid, info["name"]) 
            for pid, info in game_state["players"].items() 
            if info["is_alive"] and pid != self.role.player_id
        ]
        
        # 添加查验历史
        check_history = []
        for target_id, is_wolf in self.role.checked_players.items():
            if target_id in game_state["players"]:
                target_name = game_state["players"][target_id]["name"]
                result = "狼人" if is_wolf else "好人"
                check_history.append(f"- {target_name}: {result}")
        
        prompt = f"""
        你是预言家，现在是第 {game_state['current_round']} 回合的夜晚。
        请选择一个玩家进行查验。

        当前存活的玩家：
        {chr(10).join([f'- {name}({pid})' for pid, name in alive_players])}
        """
        
        if check_history:
            prompt += "\n\n你的查验历史："
            prompt += "\n" + "\n".join(check_history)
            
        prompt += """
        
        请选择一个你想查验的玩家，直接回复玩家ID即可。
        注意：
        1. 只能查验存活的玩家
        2. 不要查验自己
        3. 建议不要重复查验同一个玩家
        4. 用"选择[玩家ID]"格式说明查验目标
        """
        
        return prompt

class WitchAgent(BaseAIAgent):
    def __init__(self, config: Dict[str, Any], role: BaseRole):
        super().__init__(config, role)
        self.role: Witch = role  # 类型提示

    def use_potion(self, game_state: Dict[str, Any], victim_id: Optional[str] = None) -> Dict[str, Any]:
        """决定使用解药或毒药"""
        prompt = self._generate_potion_prompt(game_state, victim_id)
        response = self.ask_ai(prompt, self._get_witch_prompt())
        
        # 解析决策
        if "使用解药" in response and victim_id and self.role.can_save():
            return {
                "type": "save",
                "target": victim_id,
                "reason": response
            }
        elif "使用毒药" in response and self.role.can_poison():
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

    def _generate_discussion_prompt(self, game_state: Dict[str, Any]) -> str:
        base_prompt = super()._generate_discussion_prompt(game_state)
        
        # 添加女巫特殊状态
        witch_status = []
        if self.role.has_medicine:
            witch_status.append("解药未使用")
        if self.role.has_poison:
            witch_status.append("毒药未使用")
        
        if witch_status:
            base_prompt += "\n\n你的技能状态："
            base_prompt += "\n" + "\n".join(witch_status)
        
        return base_prompt

    def _generate_vote_prompt(self, game_state: Dict[str, Any]) -> str:
        base_prompt = super()._generate_vote_prompt(game_state)
        
        # 添加女巫特殊状态
        witch_status = []
        if self.role.has_medicine:
            witch_status.append("解药未使用")
        if self.role.has_poison:
            witch_status.append("毒药未使用")
        
        if witch_status:
            base_prompt += "\n\n你的技能状态："
            base_prompt += "\n" + "\n".join(witch_status)
        
        return base_prompt

class HunterAgent(BaseAIAgent):
    def __init__(self, config: Dict[str, Any], role: BaseRole):
        super().__init__(config, role)
        self.role: Hunter = role  # 类型提示

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

    def _generate_discussion_prompt(self, game_state: Dict[str, Any]) -> str:
        base_prompt = super()._generate_discussion_prompt(game_state)
        
        # 添加猎人特殊状态
        hunter_status = []
        if self.role.can_shoot:
            hunter_status.append("猎枪未使用")
        else:
            hunter_status.append("猎枪已使用")
        
        if hunter_status:
            base_prompt += "\n\n你的技能状态："
            base_prompt += "\n" + "\n".join(hunter_status)
        
        return base_prompt

    def _generate_vote_prompt(self, game_state: Dict[str, Any]) -> str:
        base_prompt = super()._generate_vote_prompt(game_state)
        
        # 添加猎人特殊状态
        hunter_status = []
        if self.role.can_shoot:
            hunter_status.append("猎枪未使用")
        else:
            hunter_status.append("猎枪已使用")
        
        if hunter_status:
            base_prompt += "\n\n你的技能状态："
            base_prompt += "\n" + "\n".join(hunter_status)
        
        return base_prompt

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
