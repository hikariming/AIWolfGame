from typing import Dict, List, Optional
import time
import logging
from .roles import BaseRole, Werewolf, Villager, RoleType, Seer, Witch, Hunter
from .ai_players import create_ai_agent, BaseAIAgent
import random
import re
from utils.logger import GameLogger

class GameController:
    def __init__(self, config: Dict):
        self.config = config
        self.players: Dict[str, BaseRole] = {}
        self.ai_agents: Dict[str, BaseAIAgent] = {}
        self.current_round = 1
        self.game_state = {
            "current_round": self.current_round,
            "phase": "night",
            "players": {},
            "alive_count": {"werewolf": 0, "villager": 0},
            "history": [],  # 游戏历史记录
            "vote_stats": {  # 新增：投票统计
                "total_votes": 0,
                "invalid_votes": 0,
                "player_stats": {}  # 每个玩家的投票统计
            }
        }
        self.logger = logging.getLogger(__name__)
        self.delay = config.get("delay", 1.0)  # 动作延迟时间
        
        # 初始化评估指标记录器
        self.metrics_logger = GameLogger(debug=config.get("debug", False))

    def _log_role_recognition(self, player_id: str, target_id: str, guess_is_wolf: bool):
        """记录角色识别准确率"""
        actual_is_wolf = self.players[target_id].is_wolf()
        is_correct = guess_is_wolf == actual_is_wolf
        self.metrics_logger.log_role_recognition(player_id, is_correct)

    def _log_deception_attempt(self, wolf_id: str, is_successful: bool):
        """记录狼人欺骗成功率"""
        self.metrics_logger.log_deception_attempt(wolf_id, is_successful)

    def _log_vote(self, voter_id: str, target_id: str):
        """记录投票准确率"""
        voter_is_wolf = self.players[voter_id].is_wolf()
        target_is_wolf = self.players[target_id].is_wolf()
        # 好人投狼人或狼人投好人都算正确
        is_correct = voter_is_wolf != target_is_wolf
        self.metrics_logger.log_vote(voter_id, target_id, is_correct)

    def _log_communication(self, player_id: str, message_id: str, influenced_others: bool):
        """记录沟通效果"""
        self.metrics_logger.log_communication(player_id, message_id, influenced_others)

    def _log_survival(self, player_id: str):
        """记录生存率"""
        self.metrics_logger.log_survival(player_id, self.current_round, self.config.get("total_rounds", 100))

    def _log_ability_usage(self, player_id: str, ability_type: str, is_correct: bool):
        """记录能力使用准确率"""
        self.metrics_logger.log_ability_usage(player_id, ability_type, is_correct)

    def _log_invalid_vote(self, player_id: str, reason: str):
        """记录无效投票
        
        Args:
            player_id: 投票者ID
            reason: 无效原因
        """
        if player_id not in self.game_state["vote_stats"]["player_stats"]:
            self.game_state["vote_stats"]["player_stats"][player_id] = {
                "total_votes": 0,
                "invalid_votes": 0,
                "invalid_reasons": []
            }
        
        stats = self.game_state["vote_stats"]["player_stats"][player_id]
        stats["total_votes"] += 1
        stats["invalid_votes"] += 1
        stats["invalid_reasons"].append({
            "round": self.current_round,
            "reason": reason
        })
        
        self.game_state["vote_stats"]["total_votes"] += 1
        self.game_state["vote_stats"]["invalid_votes"] += 1

    def _log_valid_vote(self, player_id: str):
        """记录有效投票"""
        if player_id not in self.game_state["vote_stats"]["player_stats"]:
            self.game_state["vote_stats"]["player_stats"][player_id] = {
                "total_votes": 0,
                "invalid_votes": 0,
                "invalid_reasons": []
            }
        
        self.game_state["vote_stats"]["player_stats"][player_id]["total_votes"] += 1
        self.game_state["vote_stats"]["total_votes"] += 1

    def initialize_game(self) -> None:
        """初始化游戏，创建角色和AI代理"""
        # 创建角色和AI代理
        for role_type, players in self.config["roles"].items():
            for player_id, info in players.items():
                # 根据角色类型创建对应的角色实例
                if role_type == "werewolf":
                    role = Werewolf(player_id, info["name"])
                    self.game_state["alive_count"]["werewolf"] += 1
                elif role_type == "seer":
                    role = Seer(player_id, info["name"])
                    self.game_state["alive_count"]["villager"] += 1
                elif role_type == "witch":
                    role = Witch(player_id, info["name"])
                    self.game_state["alive_count"]["villager"] += 1
                elif role_type == "hunter":
                    role = Hunter(player_id, info["name"])
                    self.game_state["alive_count"]["villager"] += 1
                else:
                    role = Villager(player_id, info["name"])
                    self.game_state["alive_count"]["villager"] += 1
                
                self.players[player_id] = role
                self.game_state["players"][player_id] = {
                    "name": info["name"],
                    "is_alive": True,
                    "role": role_type
                }
                
                # 获取AI配置
                ai_type = info.get("ai_type")
                if not ai_type:
                    self.logger.warning(f"玩家 {player_id} 没有指定AI类型，使用默认配置")
                    ai_type = "default"
                
                if ai_type not in self.config["ai_players"]:
                    raise ValueError(f"未知的AI类型: {ai_type}")
                
                ai_config = self.config["ai_players"][ai_type]
                self.ai_agents[player_id] = create_ai_agent(ai_config, role)

        # 设置狼人队友信息
        wolf_players = [pid for pid, role in self.players.items() if role.is_wolf()]
        for wolf_id in wolf_players:
            agent = self.ai_agents[wolf_id]
            if hasattr(agent, 'team_members'):
                agent.team_members = [p for p in wolf_players if p != wolf_id]

    def run_game(self) -> None:
        """运行游戏主循环"""
        self.initialize_game()
        
        while not self.check_game_over():
            self.game_state["current_round"] = self.current_round
            print(f"\n=== 第 {self.current_round} 回合 ===")
            
            # 夜晚阶段
            self.night_phase()
            if self.check_game_over():
                break
                
            # 白天阶段
            self.day_phase()
            
            self.current_round += 1
            time.sleep(self.delay)  # 回合间延迟
        
        self.announce_winner()

    def night_phase(self) -> None:
        """夜晚阶段：狼人杀人，神职技能"""
        print("\n=== 夜晚降临 ===")
        self.game_state["phase"] = "night"
        time.sleep(self.delay)

        # 获取存活的狼人和神职玩家
        wolves = [pid for pid, role in self.players.items() 
                 if role.is_wolf() and role.is_alive]
        seers = [pid for pid, role in self.players.items() 
                if isinstance(role, Seer) and role.is_alive]
        witches = [pid for pid, role in self.players.items() 
                  if isinstance(role, Witch) and role.is_alive]
        hunters = [pid for pid, role in self.players.items()
                  if isinstance(role, Hunter) and role.is_alive]
        
        victim_id = None  # 狼人的目标
        saved_by_witch = False  # 是否被女巫救活
        poisoned_by_witch = None  # 女巫毒死的玩家

        # 狼人行动
        if wolves:
            print("\n狼人们正在商讨...")
            time.sleep(self.delay)
            
            # 狼人讨论
            wolf_opinions = []
            wolf_targets = []  # 收集所有狼人的目标
            
            for wolf_id in wolves:
                agent = self.ai_agents[wolf_id]
                result = agent.discuss(self.game_state)
                
                if result["type"] == "kill":
                    print(f"\n{self.players[wolf_id].name} 的想法：")
                    print(result["content"])
                    target = result.get("target")
                    if target:
                        wolf_targets.append(target)
                    wolf_opinions.append({
                        "wolf": self.players[wolf_id].name,
                        "opinion": result["content"],
                        "target": target
                    })
                
                time.sleep(self.delay)
            
            # 第一回合只确认身份，不杀人
            if self.current_round == 1:
                print("\n第一个夜晚，狼人互相确认身份")
                self.game_state["history"].append({
                    "round": self.current_round,
                    "phase": "night",
                    "event": "wolf_identify",
                    "opinions": wolf_opinions
                })
                victim_id = None
            else:
                # 如果有多个狼人，随机选择一个目标
                if wolf_targets:
                    victim_id = random.choice(wolf_targets)
                    self._log_deception_attempt(wolves[0], True)
        
        # 预言家行动
        if seers:
            print("\n预言家正在行动...")
            for seer_id in seers:
                agent = self.ai_agents[seer_id]
                seer = self.players[seer_id]
                result = agent.check_player(self.game_state)
                
                if result["type"] == "check" and result["target"]:
                    target_id = result["target"]
                    
                    # 检查是否可以查验
                    if seer.can_check(target_id):
                        target_role = self.players[target_id]
                        is_wolf = target_role.is_wolf()
                        # 记录查验结果
                        seer.check_role(target_id)
                        # 记录预言家的查验准确率
                        self._log_ability_usage(seer_id, "查验", True)
                        self._log_role_recognition(seer_id, target_id, is_wolf)
                        
                        print(f"\n{self.players[seer_id].name} 查验了 {self.players[target_id].name}")
                        print(f"查验结果：{'是狼人' if is_wolf else '是好人'}")
                        
                        # 记录查验结果
                        self.game_state["history"].append({
                            "round": self.current_round,
                            "phase": "night",
                            "event": "seer_check",
                            "seer": seer_id,
                            "target": target_id,
                            "is_wolf": is_wolf
                        })
                    else:
                        print(f"\n{self.players[seer_id].name} 选择的查验目标无效")
                
                time.sleep(self.delay)
        
        # 如果有人被狼人杀死
        if victim_id:
            print(f"\n今晚，{self.players[victim_id].name} 被狼人袭击了...")
            # 女巫行动
            if witches:
                print("\n女巫正在行动...")
                for witch_id in witches:
                    agent = self.ai_agents[witch_id]
                    witch = self.players[witch_id]
                    result = agent.use_potion(self.game_state, victim_id)
                    
                    if result["type"] == "save":
                        # 检查是否可以使用解药
                        if witch.can_save(is_first_night=self.current_round == 1):
                            saved_by_witch = True
                            witch.use_medicine()
                            # 记录女巫的救人
                            self._log_ability_usage(witch_id, "救人", True)
                            print(f"\n{self.players[witch_id].name} 使用了解药，救活了 {self.players[victim_id].name}")
                        else:
                            if not witch.has_medicine:
                                print(f"\n{self.players[witch_id].name} 的解药已经用完了")
                            elif witch.used_medicine_this_round:
                                print(f"\n{self.players[witch_id].name} 本回合已经使用过解药")
                            else:
                                print(f"\n{self.players[witch_id].name} 选择不使用解药")
                    elif result["type"] == "poison" and result["target"]:
                        # 检查是否可以使用毒药
                        if witch.can_poison(is_first_night=self.current_round == 1):
                            poisoned_by_witch = result["target"]
                            witch.use_poison()
                            # 记录女巫的毒人
                            self._log_ability_usage(witch_id, "毒人", True)
                            print(f"\n{self.players[witch_id].name} 使用了毒药")
                            if self.current_round == 1:
                                print("【系统提示】第一晚使用毒药可能不是最佳选择")
                        else:
                            if not witch.has_poison:
                                print(f"\n{self.players[witch_id].name} 的毒药已经用完了")
                            else:
                                print(f"\n{self.players[witch_id].name} 选择不使用毒药")
                    
                    # 记录女巫行动
                    self.game_state["history"].append({
                        "round": self.current_round,
                        "phase": "night",
                        "event": "witch_action",
                        "witch": witch_id,
                        "action_type": result["type"],
                        "target": result["target"] if "target" in result else None,
                        "success": saved_by_witch or poisoned_by_witch is not None
                    })
                    
                    # 重置女巫的回合状态
                    witch.reset_round()
                    
                    time.sleep(self.delay)
        
        # 处理夜晚死亡
        night_deaths = []
        
        # 处理狼人杀人
        if victim_id and not saved_by_witch:
            night_deaths.append((victim_id, "被狼人杀死"))
        
        # 处理女巫毒人
        if poisoned_by_witch:
            night_deaths.append((poisoned_by_witch, "被毒死"))
        
        # 执行死亡
        for player_id, reason in night_deaths:
            self._handle_death(player_id, reason)
            
            # 如果死者是猎人，确认其死亡状态
            if isinstance(self.players[player_id], Hunter):
                hunter = self.players[player_id]
                hunter.confirm_death()
                
                # 让猎人开枪
                if hunter.can_use_gun():
                    print(f"\n{hunter.name} 倒下的瞬间，抽出了猎枪...")
                    agent = self.ai_agents[player_id]
                    result = agent.shoot(self.game_state)
                    
                    if result["type"] == "shoot" and result["target"]:
                        target_id = result["target"]
                        if target_id in self.players and self.players[target_id].is_alive:
                            hunter.use_gun()
                            self._log_ability_usage(player_id, "开枪", True)
                            print(f"\n{hunter.name} 对准了 {self.players[target_id].name}...")
                            time.sleep(self.delay)
                            print("砰！一声枪响...")
                            time.sleep(self.delay)
                            print(f"{self.players[target_id].name} 被猎人射杀")
                            self._handle_death(target_id, "被猎人射杀")
                        else:
                            print(f"\n{hunter.name} 的目标无效，猎枪未能发射")
                    else:
                        print(f"\n{hunter.name} 没有开枪，带着遗憾离开了")
                else:
                    if not hunter.can_shoot:
                        print(f"\n{hunter.name} 已经开过枪了")
                    else:
                        print(f"\n{hunter.name} 没有机会开枪就离开了")

    def _handle_death(self, player_id: str, reason: str) -> None:
        """处理玩家死亡"""
        role = self.players[player_id]
        role.is_alive = False
        
        # 更新存活计数
        if role.is_wolf():
            self.game_state["alive_count"]["werewolf"] -= 1
        else:
            self.game_state["alive_count"]["villager"] -= 1
        
        # 更新游戏状态
        self.game_state["players"][player_id]["is_alive"] = False
        
        # 记录死亡信息
        self.game_state["history"].append({
            "round": self.current_round,
            "phase": "night" if self.game_state["phase"] == "night" else "day",
            "event": "death",
            "player": player_id,
            "reason": reason
        })
        
        print(f"\n{role.name} {reason}")
        
        # 记录生存率
        self._log_survival(player_id)

    def day_phase(self) -> None:
        """白天阶段：玩家轮流发言后进行投票"""
        print("\n=== 天亮了 ===")
        self.game_state["phase"] = "day"
        time.sleep(self.delay)

        # 轮流发言
        self.discussion_phase()
        
        # 投票环节
        self.voting_phase()

    def _validate_speech(self, speech: str) -> bool:
        """验证发言是否符合要求"""
        # 移除动作描写【】中的内容后检查发言长度
        clean_speech = re.sub(r'【.*?】', '', speech)
        return len(clean_speech) >= 20

    def discussion_phase(self) -> None:
        """玩家轮流发言阶段"""
        print("\n=== 开始轮流发言 ===")
        time.sleep(self.delay)
        
        # 记录所有发言
        round_speeches = []
        
        # 第一轮发言
        alive_players = [pid for pid, role in self.players.items() if role.is_alive]
        print("\n【第一轮发言】")
        for player_id in alive_players:
            role = self.players[player_id]
            agent = self.ai_agents[player_id]
            
            # 检查玩家是否有发言权
            if not role.is_alive:
                continue
            
            print(f"\n{role.name} 的发言：")
            result = agent.discuss(self.game_state)
            
            # 处理不同类型的返回结果
            if isinstance(result, dict):
                speech = result.get("content", "")
            else:
                speech = result
            
            # 验证发言长度
            if not self._validate_speech(speech):
                self.logger.warning(f"{role.name} 的发言太短，要求重新发言")
                continue
            
            print(speech)
            
            # 记录发言
            message_id = f"{self.current_round}_{player_id}_{len(round_speeches)}"
            round_speeches.append({
                "player": role.name,
                "role": role.role_type.value,
                "content": speech,
                "message_id": message_id
            })
            
            # 评估发言的影响力
            influenced_others = self._evaluate_speech_influence(speech, player_id)
            self._log_communication(player_id, message_id, influenced_others)
            
            # 更新游戏状态
            self.game_state["history"].append({
                "round": self.current_round,
                "phase": "discussion",
                "player": player_id,
                "content": speech
            })
            
            time.sleep(self.delay)
        
        # 更新游戏状态，加入当前讨论记录
        self.game_state["current_discussion"] = round_speeches
        
        # 第二轮发言（补充发言）
        print("\n【第二轮发言】")
        for player_id in alive_players:
            role = self.players[player_id]
            agent = self.ai_agents[player_id]
            
            # 检查玩家是否有发言权
            if not role.is_alive:
                continue
            
            print(f"\n{role.name} 要补充发言吗？")
            result = agent.discuss(self.game_state)
            
            # 处理不同类型的返回结果
            if isinstance(result, dict):
                speech = result.get("content", "")
            else:
                speech = result
            
            if len(speech) > 50:  # 如果有实质性的补充
                print(speech)
                round_speeches.append({
                    "player": role.name,
                    "role": role.role_type.value,
                    "content": speech
                })
                
                # 更新游戏状态
                self.game_state["history"].append({
                    "round": self.current_round,
                    "phase": "discussion",
                    "player": player_id,
                    "content": speech
                })
            else:
                print("无补充发言")
            
            time.sleep(self.delay)

    def _evaluate_speech_influence(self, speech: str, speaker_id: str) -> bool:
        """评估发言的影响力
        
        通过分析发言内容和其他玩家的反应来判断发言是否有影响力
        """
        # 基本规则：
        # 1. 发言包含具体的分析和推理
        # 2. 提供了新的信息或视角
        # 3. 引起了其他玩家的回应
        has_analysis = len(re.findall(r'我认为|我觉得|我分析|根据|因为|所以', speech)) > 0
        has_new_info = len(re.findall(r'发现|注意到|观察到|怀疑|证据', speech)) > 0
        is_logical = len(re.findall(r'如果|那么|因此|证明|说明', speech)) > 0
        
        # 发言质量评分
        score = 0
        if has_analysis: score += 1
        if has_new_info: score += 1
        if is_logical: score += 1
        if len(speech) > 100: score += 1  # 较长的发言通常包含更多信息
        
        return score >= 2  # 得分达到2分以上认为是有影响力的发言

    def voting_phase(self) -> None:
        """投票环节"""
        print("\n=== 开始投票 ===")
        print("\n请各位玩家依次进行投票...")
        time.sleep(self.delay)
        
        votes = {}
        vote_details = []
        
        # 只有存活玩家才能投票
        alive_players = [pid for pid, role in self.players.items() if role.is_alive]
        
        # 显示存活玩家列表
        print("\n当前存活玩家：")
        for pid in alive_players:
            print(f"- {self.players[pid].name} (ID: {pid})")
        print("\n开始投票...")
        
        # 获取本轮讨论内容
        current_round_discussions = []
        for event in self.game_state["history"]:
            if (event.get("round") == self.current_round and 
                event.get("phase") == "discussion" and 
                event.get("content")):
                current_round_discussions.append({
                    "player": self.players[event["player"]].name,
                    "content": event["content"]
                })
        
        for player_id in alive_players:
            role = self.players[player_id]
            agent = self.ai_agents[player_id]
            
            # 再次检查玩家是否存活
            if not role.is_alive:
                continue
            
            # 最多尝试3次投票
            max_attempts = 3
            current_attempt = 0
            valid_vote = False
            
            while not valid_vote and current_attempt < max_attempts:
                current_attempt += 1
                
                if current_attempt == 1:
                    print(f"\n轮到 {role.name} 投票...")
                else:
                    print(f"\n{role.name} 第 {current_attempt} 次尝试投票...")
                
                # 为AI提供投票提示和上下文
                vote_context = {
                    "type": "vote_context",
                    "current_round": self.current_round,
                    "voter": {
                        "id": player_id,
                        "name": role.name
                    },
                    "alive_players": [
                        {
                            "id": pid,
                            "name": self.players[pid].name
                        }
                        for pid in alive_players if pid != player_id
                    ],
                    "discussions": current_round_discussions,
                    "retry_count": current_attempt,
                    "message": f"请根据本轮讨论内容进行投票，注意：\n"
                             f"1. 不能投票给自己 ({player_id})\n"
                             f"2. 只能投票给存活的玩家\n"
                             f"3. 必须使用正确的玩家ID格式\n"
                             f"\n本轮讨论内容：\n" +
                             "\n".join([f"{disc['player']}: {disc['content']}" 
                                      for disc in current_round_discussions]) +
                             f"\n\n当前存活玩家：\n" +
                             "\n".join([f"- {self.players[pid].name} (ID: {pid})" 
                                      for pid in alive_players if pid != player_id])
                }
                self.game_state["vote_context"] = vote_context
                
                # 获取投票目标和投票理由
                vote_result = agent.vote(self.game_state)
                target_id = vote_result.get("target")
                reason = vote_result.get("reason", "没有给出具体理由")
                
                # 验证投票目标的有效性
                if target_id:
                    if target_id == player_id:
                        print(f"【错误】不能投票给自己")
                        self._log_invalid_vote(player_id, "自投")
                    elif target_id not in self.players:
                        print(f"【错误】目标ID {target_id} 不存在")
                        self._log_invalid_vote(player_id, "目标ID不存在")
                    elif not self.players[target_id].is_alive:
                        print(f"【错误】目标玩家 {self.players[target_id].name} 已经死亡")
                        self._log_invalid_vote(player_id, "目标已死亡")
                    else:
                        valid_vote = True
                        self._log_valid_vote(player_id)
                        votes[target_id] = votes.get(target_id, 0) + 1
                        vote_detail = {
                            "voter": player_id,
                            "voter_name": role.name,
                            "voter_role": role.role_type.value,
                            "target": target_id,
                            "target_name": self.players[target_id].name,
                            "reason": reason,
                            "attempts": current_attempt
                        }
                        print(f"{role.name} 投票给了 {self.players[target_id].name}")
                        print(f"投票理由：{reason}")
                        vote_details.append(vote_detail)
                        
                        # 记录投票准确率
                        self._log_vote(player_id, target_id)
                else:
                    print(f"【错误】未能识别有效的投票目标")
                    self._log_invalid_vote(player_id, "无效的投票格式")
            
            # 如果三次尝试后仍未有效投票，记录为随机投票
            if not valid_vote:
                self._log_invalid_vote(player_id, "三次尝试失败，随机投票")
                possible_targets = [pid for pid in alive_players if pid != player_id]
                if possible_targets:
                    target_id = random.choice(possible_targets)
                    votes[target_id] = votes.get(target_id, 0) + 1
                    print(f"\n【系统】{role.name} 三次投票均无效")
                    print(f"【系统】随机指定投票给 {self.players[target_id].name}")
                    vote_detail = {
                        "voter": player_id,
                        "voter_name": role.name,
                        "voter_role": role.role_type.value,
                        "target": target_id,
                        "target_name": self.players[target_id].name,
                        "reason": "三次投票无效，系统随机指定",
                        "attempts": current_attempt
                    }
                    vote_details.append(vote_detail)
                    self._log_vote(player_id, target_id)
                else:
                    self.logger.warning(f"{role.name} 无法进行有效投票：没有合适的目标")
            
            # 清除投票上下文
            if "vote_context" in self.game_state:
                del self.game_state["vote_context"]
            
            time.sleep(self.delay)

        # 统计投票结果
        if votes:
            # 找出票数最多的玩家
            max_votes = max(votes.values())
            most_voted = [pid for pid, count in votes.items() if count == max_votes]
            
            print("\n=== 投票结果统计 ===")
            print("\n得票情况：")
            for pid, count in votes.items():
                print(f"- {self.players[pid].name}: {count} 票")
                # 显示投给该玩家的人
                voters = [detail["voter_name"] for detail in vote_details if detail["target"] == pid]
                print(f"  投票者: {', '.join(voters)}")
            
            if len(most_voted) > 1:
                print("\n【警告】出现平票！")
                print(f"平票玩家：{', '.join([self.players[pid].name for pid in most_voted])}")
                # 随机选择一个
                voted_out = random.choice(most_voted)
                print(f"\n随机选择了 {self.players[voted_out].name}")
            else:
                voted_out = most_voted[0]
                print(f"\n投票最高的是 {self.players[voted_out].name}，得到 {max_votes} 票")
            
            print(f"\n{self.players[voted_out].name} 被投票出局")
            
            # 记录投票结果
            self.game_state["history"].append({
                "round": self.current_round,
                "phase": "vote",
                "votes": vote_details,
                "result": voted_out,
                "is_tie": len(most_voted) > 1,
                "vote_counts": {pid: count for pid, count in votes.items()},
                "voting_process": {
                    "total_attempts": sum(detail["attempts"] for detail in vote_details),
                    "invalid_votes": len([d for d in vote_details if d["attempts"] > 1]),
                    "discussions": current_round_discussions
                },
                "vote_stats": self.game_state["vote_stats"]  # 添加投票统计到历史记录
            })
            
            # 处理出局，允许发表遗言
            self.kill_player(voted_out, "公投出局", allow_last_words=True)

    def kill_player(self, player_id: str, reason: str, allow_last_words: bool = True) -> None:
        """处理玩家死亡
        
        Args:
            player_id: 死亡玩家ID
            reason: 死亡原因
            allow_last_words: 是否允许发表遗言
        """
        if player_id in self.players:
            player = self.players[player_id]
            player.is_alive = False
            self.game_state["players"][player_id]["is_alive"] = False
            
            # 记录生存率
            self._log_survival(player_id)
            
            if player.is_wolf():
                self.game_state["alive_count"]["werewolf"] -= 1
            else:
                self.game_state["alive_count"]["villager"] -= 1
            
            print(f"\n{player.name} 被{reason}")
            
            # 处理遗言
            if allow_last_words:
                # 第一天晚上死亡或白天死亡的玩家可以发表遗言
                if self.current_round == 1 or reason == "公投出局":
                    print(f"\n{player.name} 的遗言：")
                    agent = self.ai_agents[player_id]
                    last_words = agent.last_words(self.game_state)
                    print(last_words)
                    
                    # 记录遗言
                    self.game_state["history"].append({
                        "round": self.current_round,
                        "phase": self.game_state["phase"],
                        "event": "last_words",
                        "player": player_id,
                        "content": last_words
                    })
            
            # 记录死亡信息
            self.game_state["history"].append({
                "round": self.current_round,
                "phase": self.game_state["phase"],
                "event": "death",
                "player": player_id,
                "reason": reason
            })
            
            time.sleep(self.delay)

    def check_game_over(self) -> bool:
        """检查游戏是否结束"""
        wolf_count = self.game_state["alive_count"]["werewolf"]
        villager_count = self.game_state["alive_count"]["villager"]
        
        if wolf_count == 0:
            return True
        if wolf_count >= villager_count:
            return True
        return False

    def announce_winner(self) -> None:
        """宣布游戏结果"""
        if self.game_state["alive_count"]["werewolf"] == 0:
            winner = "好人阵营"
        else:
            winner = "狼人阵营"
            
        print(f"\n=== {winner}胜利！===")
        
        # 打印存活玩家
        print("\n存活玩家：")
        for player_id, role in self.players.items():
            if role.is_alive:
                print(f"- {role.name} ({role.role_type.value})")
        
        # 打印投票统计
        print("\n=== 投票统计 ===")
        total_votes = self.game_state["vote_stats"]["total_votes"]
        invalid_votes = self.game_state["vote_stats"]["invalid_votes"]
        if total_votes > 0:
            invalid_rate = (invalid_votes / total_votes) * 100
            print(f"\n总体投票无效率: {invalid_rate:.1f}%")
            print(f"总投票数: {total_votes}")
            print(f"无效投票数: {invalid_votes}")
            
            print("\n各玩家投票统计：")
            for player_id, stats in self.game_state["vote_stats"]["player_stats"].items():
                player_name = self.players[player_id].name
                player_total = stats["total_votes"]
                player_invalid = stats["invalid_votes"]
                if player_total > 0:
                    player_invalid_rate = (player_invalid / player_total) * 100
                    print(f"\n{player_name}:")
                    print(f"- 投票无效率: {player_invalid_rate:.1f}%")
                    print(f"- 总投票数: {player_total}")
                    print(f"- 无效投票数: {player_invalid}")
                    if player_invalid > 0:
                        print("- 无效原因统计:")
                        reason_counts = {}
                        for record in stats["invalid_reasons"]:
                            reason = record["reason"]
                            reason_counts[reason] = reason_counts.get(reason, 0) + 1
                        for reason, count in reason_counts.items():
                            print(f"  * {reason}: {count}次")
        
        # 记录游戏结果
        self.game_state["history"].append({
            "round": self.current_round,
            "event": "game_over",
            "winner": winner,
            "vote_stats": self.game_state["vote_stats"]  # 添加投票统计到历史记录
        }) 