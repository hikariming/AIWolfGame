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

from typing import Dict, List, Optional
import time
import logging
from .roles import BaseRole, Werewolf, Villager, RoleType
from .ai_players import create_ai_agent, WerewolfAgent, VillagerAgent

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
                
                ai_config = self.config["ai_players"][info["ai_type"]]
                self.ai_agents[player_id] = create_ai_agent(ai_config, role)

        # 设置狼人队友信息
        wolf_players = [pid for pid, role in self.players.items() if role.is_wolf()]
        for wolf_id in wolf_players:
            if isinstance(self.ai_agents[wolf_id], WerewolfAgent):
                self.ai_agents[wolf_id].team_members = [p for p in wolf_players if p != wolf_id]

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
            print("\n狼人们正在商讨目标...")
            time.sleep(self.delay)
            
            # 狼人讨论
            for wolf_id in wolves:
                agent = self.ai_agents[wolf_id]
                if isinstance(agent, WerewolfAgent):
                    target_id = agent.discuss_kill(self.game_state)
                    print(f"\n{self.players[wolf_id].name} 的想法：")
                    print(f"{target_id}")
                    time.sleep(self.delay)
            
            # 取第一个狼人的决定作为最终决定
            final_target = self.ai_agents[wolves[0]].discuss_kill(self.game_state)
            if final_target:
                self.kill_player(final_target, "狼人袭击")

    def day_phase(self) -> None:
        """白天阶段：玩家轮流发言后进行投票"""
        print("\n=== 天亮了 ===")
        self.game_state["phase"] = "day"
        time.sleep(self.delay)

        # 轮流发言
        self.discussion_phase()
        
        # 投票环节
        print("\n=== 开始投票 ===")
        time.sleep(self.delay)
        
        votes = {}
        # 收集所有存活玩家的投票
        for player_id, role in self.players.items():
            if role.is_alive:
                agent = self.ai_agents[player_id]
                target_id = agent.discuss_vote(self.game_state)
                votes[target_id] = votes.get(target_id, 0) + 1
                print(f"{role.name} 投票给了 {self.players[target_id].name}")
                time.sleep(self.delay)

        # 处理投票结果
        if votes:
            voted_out = max(votes.items(), key=lambda x: x[1])[0]
            print(f"\n投票结果：{self.players[voted_out].name} 被投票出局")
            self.kill_player(voted_out, "公投出局")

    def discussion_phase(self) -> None:
        """玩家轮流发言阶段"""
        print("\n=== 开始轮流发言 ===")
        time.sleep(self.delay)
        
        # 按照玩家ID顺序发言
        alive_players = [pid for pid, role in self.players.items() if role.is_alive]
        for player_id in alive_players:
            role = self.players[player_id]
            agent = self.ai_agents[player_id]
            
            print(f"\n{role.name} 的发言：")
            speech = agent.discuss_vote(self.game_state)  # 使用投票讨论作为发言内容
            print(speech)
            
            # 记录发言到游戏历史
            self.game_state["history"].append({
                "round": self.current_round,
                "phase": "discussion",
                "player": player_id,
                "content": speech
            })
            
            time.sleep(self.delay)

    def kill_player(self, player_id: str, reason: str) -> None:
        """处理玩家死亡"""
        if player_id in self.players:
            player = self.players[player_id]
            player.is_alive = False
            self.game_state["players"][player_id]["is_alive"] = False
            
            if player.is_wolf():
                self.game_state["alive_count"]["werewolf"] -= 1
            else:
                self.game_state["alive_count"]["villager"] -= 1
            
            # 记录死亡信息
            self.game_state["history"].append({
                "round": self.current_round,
                "phase": self.game_state["phase"],
                "event": "death",
                "player": player_id,
                "reason": reason
            })
            
            print(f"\n{player.name} 被{reason}死亡")
            time.sleep(self.delay)

    def check_game_over(self) -> bool:
        """检查游戏是否结束"""
        wolf_count = self.game_state["alive_count"]["werewolf"]
        villager_count = self.game_state["alive_count"]["villager"]
        
        return wolf_count == 0 or wolf_count >= villager_count

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