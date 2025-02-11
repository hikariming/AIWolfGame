from typing import Dict, List, Optional
import time
import logging
from .roles import BaseRole, Werewolf, Villager, RoleType
from .ai_players import create_ai_agent, BaseAIAgent
import random
import re

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
            "history": []  # 游戏历史记录
        }
        self.logger = logging.getLogger(__name__)
        self.delay = config.get("delay", 1.0)  # 动作延迟时间

    def initialize_game(self) -> None:
        """初始化游戏，创建角色和AI代理"""
        # 创建角色和AI代理
        for role_type, players in self.config["roles"].items():
            for player_id, info in players.items():
                if role_type == "werewolf":
                    role = Werewolf(player_id, info["name"])
                    self.game_state["alive_count"]["werewolf"] += 1
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
                ai_type = info["ai_type"]
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
        """夜晚阶段：狼人讨论并杀人"""
        print("\n=== 夜晚降临 ===")
        self.game_state["phase"] = "night"
        time.sleep(self.delay)

        # 获取存活的狼人
        wolves = [pid for pid, role in self.players.items() 
                 if role.is_wolf() and role.is_alive]
        
        if wolves:
            print("\n狼人们正在商讨...")
            time.sleep(self.delay)
            
            # 狼人讨论
            wolf_opinions = []
            final_target = None
            
            for wolf_id in wolves:
                agent = self.ai_agents[wolf_id]
                result = agent.discuss(self.game_state)
                
                if result["type"] == "kill":
                    print(f"\n{self.players[wolf_id].name} 的想法：")
                    print(result["content"])
                    wolf_opinions.append({
                        "wolf": self.players[wolf_id].name,
                        "opinion": result["content"],
                        "target": result.get("target")
                    })
                    if final_target is None and result.get("target"):
                        final_target = result["target"]
                
                time.sleep(self.delay)
            
            # 第一回合只确认身份，不杀人
            if self.current_round == 1:
                print("\n第一个夜晚，狼人互相确认身份")
                # 记录到游戏历史
                self.game_state["history"].append({
                    "round": self.current_round,
                    "phase": "night",
                    "event": "wolf_identify",
                    "opinions": wolf_opinions
                })
                return
            
            # 显示最终决定
            if final_target and final_target in self.players:
                print(f"\n狼人们最终决定击杀 {self.players[final_target].name}")
                self.kill_player(final_target, "狼人袭击", allow_last_words=False)
                
                # 记录这次击杀到游戏历史
                self.game_state["history"].append({
                    "round": self.current_round,
                    "phase": "night",
                    "event": "wolf_kill",
                    "opinions": wolf_opinions,
                    "target": final_target
                })

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

    def voting_phase(self) -> None:
        """投票环节"""
        print("\n=== 开始投票 ===")
        time.sleep(self.delay)
        
        votes = {}
        vote_details = []
        
        # 只有存活玩家才能投票
        alive_players = [pid for pid, role in self.players.items() if role.is_alive]
        for player_id in alive_players:
            role = self.players[player_id]
            agent = self.ai_agents[player_id]
            
            # 再次检查玩家是否存活
            if not role.is_alive:
                continue
            
            # 获取投票目标和投票理由
            vote_result = agent.vote(self.game_state)
            target_id = vote_result.get("target")
            reason = vote_result.get("reason", "没有给出具体理由")
            
            if target_id and target_id in self.players:  # 确保投票目标有效
                votes[target_id] = votes.get(target_id, 0) + 1
                vote_detail = {
                    "voter": player_id,
                    "voter_name": role.name,
                    "voter_role": role.role_type.value,
                    "target": target_id,
                    "target_name": self.players[target_id].name,
                    "reason": reason
                }
                print(f"{role.name} 投票给了 {self.players[target_id].name}，理由：{reason}")
                vote_details.append(vote_detail)
            else:
                # 如果没有有效的投票目标，随机选择一个存活玩家（除了自己）
                possible_targets = [pid for pid in alive_players if pid != player_id]
                if possible_targets:
                    target_id = random.choice(possible_targets)
                    votes[target_id] = votes.get(target_id, 0) + 1
                    print(f"{role.name} 的投票无效，随机投给了 {self.players[target_id].name}")
                self.logger.warning(f"无效的投票目标: {target_id}")
            
            time.sleep(self.delay)

        # 统计投票结果
        if votes:
            # 找出票数最多的玩家
            max_votes = max(votes.values())
            most_voted = [pid for pid, count in votes.items() if count == max_votes]
            
            print("\n投票结果统计：")
            for pid, count in votes.items():
                print(f"{self.players[pid].name}: {count}票")
            
            if len(most_voted) > 1:
                print("\n出现平票！")
                # 随机选择一个
                voted_out = random.choice(most_voted)
                print(f"随机选择了 {self.players[voted_out].name}")
            else:
                voted_out = most_voted[0]
            
            print(f"\n{self.players[voted_out].name} 被投票出局")
            
            # 记录投票结果
            self.game_state["history"].append({
                "round": self.current_round,
                "phase": "vote",
                "votes": vote_details,
                "result": voted_out,
                "is_tie": len(most_voted) > 1
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
        
        # 记录游戏结果
        self.game_state["history"].append({
            "round": self.current_round,
            "event": "game_over",
            "winner": winner
        }) 