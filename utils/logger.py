"""
日志记录器，负责记录游戏过程中的所有信息

主要职责：
1. 日志记录
   - 记录游戏流程
   - 记录玩家行为
   - 记录 AI 响应
   - 记录系统事件
   - 记录模型评估指标

2. 日志格式化
   - 控制台输出格式
   - 文件记录格式
   - 不同级别日志区分
   - 评估指标统计

3. 与其他模块的交互：
   - 被所有模块调用记录日志
   - 管理 logs 目录
   - 支持日志回放功能
   - 生成评估报告

类设计：
class GameLogger:
    def __init__(self, debug: bool = False)
    def log_round()
    def log_event()
    def log_game_over()
    def save_game_record()
""" 

import logging
import os
from datetime import datetime
from typing import Dict, Any, List
import json
import csv
import glob

class GameLogger:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.game_record = {
            "start_time": datetime.now().isoformat(),
            "rounds": [],
            "events": [],
            "final_result": None,
            "model_metrics": {},  # 新增：模型评估指标
            "game_stats": {       # 新增：游戏统计
                "total_rounds": 0,
                "total_deaths": 0,
                "ability_uses": 0,
                "votes": []
            },
            "round_records": []  # 新增：每轮详细记录
        }
        self._setup_logger()
        self._init_metrics()

    def _setup_logger(self):
        """设置日志系统"""
        # 创建必要的目录
        for dir_name in ['logs', 'test_analysis']:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
        
        # 设置日志文件名
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'logs/game_{self.timestamp}.log'
        debug_file = f'logs/debug_{self.timestamp}.log'
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 设置文件处理器 - 普通日志
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # 设置文件处理器 - 调试日志
        debug_handler = logging.FileHandler(debug_file, encoding='utf-8')
        debug_handler.setFormatter(formatter)
        debug_handler.setLevel(logging.DEBUG)
        
        # 设置控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(debug_handler)
        root_logger.addHandler(console_handler)
        
        # 记录游戏启动信息
        logging.info("=== 游戏日志系统启动 ===")
        logging.info(f"时间戳: {self.timestamp}")
        logging.info(f"调试模式: {'开启' if self.debug else '关闭'}")

    def _init_metrics(self):
        """初始化评估指标"""
        self.metrics = {
            "role_recognition": {
                "correct": 0,
                "total": 0
            },
            "deception_success": {
                "successful": 0,
                "attempts": 0
            },
            "voting_accuracy": {
                "correct": 0,
                "total": 0
            },
            "communication_effect": {
                "influential_messages": 0,
                "total_messages": 0
            },
            "survival_rate": {
                "rounds_survived": 0,
                "total_rounds": 0
            },
            "ability_usage": {
                "correct": 0,
                "total": 0
            },
            "vote_validity": {  # 新增：投票有效性指标
                "valid_votes": 0,
                "total_votes": 0,
                "player_stats": {}
            }
        }

    def log_role_recognition(self, player_id: str, is_correct: bool):
        """记录角色识别准确率"""
        self.metrics["role_recognition"]["total"] += 1
        if is_correct:
            self.metrics["role_recognition"]["correct"] += 1
        
        event = {
            "type": "role_recognition",
            "player_id": player_id,
            "is_correct": is_correct,
            "timestamp": datetime.now().isoformat()
        }
        self.game_record["events"].append(event)
        logging.debug(f"角色识别: 玩家{player_id} {'正确' if is_correct else '错误'}")

    def log_deception_attempt(self, player_id: str, is_successful: bool):
        """记录欺骗成功率"""
        self.metrics["deception_success"]["attempts"] += 1
        if is_successful:
            self.metrics["deception_success"]["successful"] += 1
            
        event = {
            "type": "deception_attempt",
            "player_id": player_id,
            "is_successful": is_successful,
            "timestamp": datetime.now().isoformat()
        }
        self.game_record["events"].append(event)
        logging.debug(f"欺骗尝试: 玩家{player_id} {'成功' if is_successful else '失败'}")

    def log_vote(self, voter_id: str, target_id: str, is_correct: bool):
        """记录投票准确率"""
        self.metrics["voting_accuracy"]["total"] += 1
        if is_correct:
            self.metrics["voting_accuracy"]["correct"] += 1
            
        vote_record = {
            "voter_id": voter_id,
            "target_id": target_id,
            "is_correct": is_correct,
            "round": self.game_record["game_stats"]["total_rounds"],
            "timestamp": datetime.now().isoformat()
        }
        self.game_record["game_stats"]["votes"].append(vote_record)
        logging.info(f"投票记录: {voter_id} -> {target_id} ({'正确' if is_correct else '错误'})")

    def log_communication(self, player_id: str, message_id: str, influenced_others: bool):
        """记录沟通效果"""
        self.metrics["communication_effect"]["total_messages"] += 1
        if influenced_others:
            self.metrics["communication_effect"]["influential_messages"] += 1
            
        event = {
            "type": "communication",
            "player_id": player_id,
            "message_id": message_id,
            "influenced_others": influenced_others,
            "timestamp": datetime.now().isoformat()
        }
        self.game_record["events"].append(event)
        logging.debug(f"沟通: 玩家{player_id}的消息{message_id} {'有影响' if influenced_others else '无影响'}")

    def log_survival(self, player_id: str, rounds_survived: int, total_rounds: int):
        """记录生存率"""
        self.metrics["survival_rate"]["rounds_survived"] += rounds_survived
        self.metrics["survival_rate"]["total_rounds"] += total_rounds
        logging.debug(f"生存: 玩家{player_id}存活{rounds_survived}/{total_rounds}轮")

    def log_ability_usage(self, player_id: str, ability_type: str, is_correct: bool):
        """记录能力使用准确率"""
        self.metrics["ability_usage"]["total"] += 1
        if is_correct:
            self.metrics["ability_usage"]["correct"] += 1
        
        self.game_record["game_stats"]["ability_uses"] += 1
        event = {
            "type": "ability_usage",
            "player_id": player_id,
            "ability_type": ability_type,
            "is_correct": is_correct,
            "timestamp": datetime.now().isoformat()
        }
        self.game_record["events"].append(event)
        logging.info(f"能力使用: 玩家{player_id}使用{ability_type} {'正确' if is_correct else '错误'}")

    def log_vote_validity(self, player_id: str, is_valid: bool, reason: str = None):
        """记录投票有效性
        
        Args:
            player_id: 投票者ID
            is_valid: 是否是有效投票
            reason: 如果无效，记录原因
        """
        self.metrics["vote_validity"]["total_votes"] += 1
        if is_valid:
            self.metrics["vote_validity"]["valid_votes"] += 1
        
        # 更新玩家统计
        if player_id not in self.metrics["vote_validity"]["player_stats"]:
            self.metrics["vote_validity"]["player_stats"][player_id] = {
                "valid_votes": 0,
                "total_votes": 0,
                "invalid_reasons": {}
            }
        
        player_stats = self.metrics["vote_validity"]["player_stats"][player_id]
        player_stats["total_votes"] += 1
        if is_valid:
            player_stats["valid_votes"] += 1
        elif reason:
            player_stats["invalid_reasons"][reason] = player_stats["invalid_reasons"].get(reason, 0) + 1
        
        # 记录事件
        event = {
            "type": "vote_validity",
            "player_id": player_id,
            "is_valid": is_valid,
            "reason": reason if not is_valid else None,
            "timestamp": datetime.now().isoformat()
        }
        self.game_record["events"].append(event)
        
        if not is_valid:
            logging.info(f"无效投票: 玩家{player_id} - 原因: {reason}")

    def calculate_metrics(self) -> Dict[str, float]:
        """计算最终评估指标"""
        results = {}
        
        # 角色识别准确率
        if self.metrics["role_recognition"]["total"] > 0:
            results["role_recognition_accuracy"] = (
                self.metrics["role_recognition"]["correct"] / 
                self.metrics["role_recognition"]["total"]
            )
            
        # 欺骗成功率
        if self.metrics["deception_success"]["attempts"] > 0:
            results["deception_success_rate"] = (
                self.metrics["deception_success"]["successful"] / 
                self.metrics["deception_success"]["attempts"]
            )
            
        # 投票准确率
        if self.metrics["voting_accuracy"]["total"] > 0:
            results["voting_accuracy"] = (
                self.metrics["voting_accuracy"]["correct"] / 
                self.metrics["voting_accuracy"]["total"]
            )
            
        # 沟通效果
        if self.metrics["communication_effect"]["total_messages"] > 0:
            results["communication_effectiveness"] = (
                self.metrics["communication_effect"]["influential_messages"] / 
                self.metrics["communication_effect"]["total_messages"]
            )
            
        # 生存率
        if self.metrics["survival_rate"]["total_rounds"] > 0:
            results["survival_rate"] = (
                self.metrics["survival_rate"]["rounds_survived"] / 
                self.metrics["survival_rate"]["total_rounds"]
            )
            
        # 能力使用准确率
        if self.metrics["ability_usage"]["total"] > 0:
            results["ability_usage_accuracy"] = (
                self.metrics["ability_usage"]["correct"] / 
                self.metrics["ability_usage"]["total"]
            )
            
        # 投票有效率
        if self.metrics["vote_validity"]["total_votes"] > 0:
            results["vote_validity_rate"] = (
                self.metrics["vote_validity"]["valid_votes"] / 
                self.metrics["vote_validity"]["total_votes"]
            )
            
            # 计算每个玩家的投票有效率
            results["player_vote_validity"] = {}
            for player_id, stats in self.metrics["vote_validity"]["player_stats"].items():
                if stats["total_votes"] > 0:
                    validity_rate = stats["valid_votes"] / stats["total_votes"]
                    results["player_vote_validity"][player_id] = {
                        "validity_rate": validity_rate,
                        "total_votes": stats["total_votes"],
                        "invalid_reasons": stats["invalid_reasons"]
                    }
            
        return results

    def log_round(self, round_num: int, phase: str, events: List[Dict]):
        """记录每个回合的信息"""
        round_record = {
            "round_number": round_num,
            "phase": phase,
            "events": events,
            "timestamp": datetime.now().isoformat()
        }
        self.game_record["rounds"].append(round_record)
        self.game_record["game_stats"]["total_rounds"] = round_num
        logging.info(f"=== 第 {round_num} 回合 {phase} 阶段 ===")
        for event in events:
            logging.info(f"事件: {event}")

    def log_event(self, event_type: str, details: Dict[str, Any]):
        """记录游戏事件"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            **details
        }
        self.game_record["events"].append(event)
        
        # 特殊事件处理
        if event_type == "death":
            self.game_record["game_stats"]["total_deaths"] += 1
            
        logging.info(f"游戏事件: {event_type}")
        for key, value in details.items():
            logging.info(f"  {key}: {value}")

    def log_game_over(self, winner: str, final_state: Dict[str, Any]):
        """记录游戏结束信息"""
        metrics = self.calculate_metrics()
        self.game_record["final_result"] = {
            "winner": winner,
            "final_state": final_state,
            "end_time": datetime.now().isoformat(),
            "metrics": metrics,
            "game_stats": self.game_record["game_stats"]
        }
        
        # 记录评估指标
        logging.info("\n=== 游戏结束 ===")
        logging.info(f"胜利方: {winner}")
        logging.info("\n游戏统计:")
        logging.info(f"总回合数: {self.game_record['game_stats']['total_rounds']}")
        logging.info(f"总死亡数: {self.game_record['game_stats']['total_deaths']}")
        logging.info(f"技能使用次数: {self.game_record['game_stats']['ability_uses']}")
        
        logging.info("\n评估指标:")
        for metric_name, value in metrics.items():
            logging.info(f"{metric_name}: {value:.2%}")
        
        # 保存游戏记录
        self.save_game_record()
        
        # 生成分析报告
        self._generate_analysis_report()

    def save_game_record(self):
        """保存完整的游戏记录"""
        # 保存详细游戏记录
        record_file = f'logs/game_record_{self.timestamp}.json'
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(self.game_record, f, ensure_ascii=False, indent=2)
            
        # 保存简要统计信息
        stats_file = f'test_analysis/game_stats_{self.timestamp}.json'
        stats = {
            "timestamp": self.timestamp,
            "metrics": self.game_record["final_result"]["metrics"],
            "game_stats": self.game_record["game_stats"],
            "winner": self.game_record["final_result"]["winner"]
        }
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
            
        # 记录单局游戏结果
        self.log_game_result()
        
        # 记录多轮游戏统计
        self.log_multi_game_stats()

    def log_game_result(self):
        """记录单局游戏结果到CSV文件"""
        # 确保目录存在
        os.makedirs('game_results', exist_ok=True)
        
        # 获取游戏结果数据
        final_result = self.game_record.get("final_result", {})
        winner = final_result.get("winner", "未知")
        metrics = final_result.get("metrics", {})
        
        # 获取玩家数据
        players_data = []
        if "final_state" in final_result and "players" in final_result["final_state"]:
            for player_id, player_info in final_result["final_state"]["players"].items():
                # 获取玩家的AI模型类型（需要从外部传入）
                ai_model = player_info.get("ai_model", "未知")
                role = player_info.get("role", "未知")
                is_alive = player_info.get("is_alive", False)
                
                # 计算该玩家是否获胜
                is_winner = False
                if (winner == "狼人阵营" and role == "werewolf") or \
                   (winner == "好人阵营" and role != "werewolf"):
                    is_winner = True
                
                # 收集玩家数据
                player_data = {
                    "player_id": player_id,
                    "name": player_info.get("name", player_id),
                    "role": role,
                    "ai_model": ai_model,
                    "is_alive": is_alive,
                    "is_winner": is_winner
                }
                players_data.append(player_data)
        
        # 创建CSV文件名
        csv_file = f'game_results/game_result_{self.timestamp}.csv'
        
        # 写入CSV文件
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            # 定义CSV列
            fieldnames = [
                "game_id", "timestamp", "winner", "total_rounds", 
                "player_id", "player_name", "role", "ai_model", "is_alive", "is_winner",
                "role_recognition_accuracy", "deception_success_rate", "voting_accuracy",
                "communication_effectiveness", "survival_rate", "ability_usage_accuracy"
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # 为每个玩家写入一行
            game_id = f"game_{self.timestamp}"
            for player in players_data:
                row = {
                    "game_id": game_id,
                    "timestamp": self.timestamp,
                    "winner": winner,
                    "total_rounds": self.game_record["game_stats"]["total_rounds"],
                    "player_id": player["player_id"],
                    "player_name": player["name"],
                    "role": player["role"],
                    "ai_model": player["ai_model"],
                    "is_alive": "是" if player["is_alive"] else "否",
                    "is_winner": "是" if player["is_winner"] else "否"
                }
                
                # 添加指标数据
                for metric_name, value in metrics.items():
                    if metric_name in fieldnames:
                        row[metric_name] = value
                
                writer.writerow(row)
        
        logging.info(f"单局游戏结果已保存到 {csv_file}")
    
    def log_multi_game_stats(self):
        """记录多轮游戏统计到CSV文件"""
        # 确保目录存在
        os.makedirs('game_stats', exist_ok=True)
        
        # 收集所有单局游戏结果文件
        game_result_files = glob.glob('game_results/game_result_*.csv')
        
        if not game_result_files:
            logging.warning("没有找到单局游戏结果文件，无法生成多轮统计")
            return
        
        # 初始化模型统计数据
        model_stats = {}
        
        # 读取所有单局游戏结果
        for result_file in game_result_files:
            with open(result_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ai_model = row.get("ai_model", "未知")
                    role = row.get("role", "未知")
                    is_winner = row.get("is_winner", "否") == "是"
                    is_alive = row.get("is_alive", "否") == "是"
                    
                    # 初始化模型数据
                    if ai_model not in model_stats:
                        model_stats[ai_model] = {
                            "total_games": 0,
                            "wins": 0,
                            "werewolf_games": 0,
                            "werewolf_wins": 0,
                            "villager_games": 0,
                            "villager_wins": 0,
                            "survival_count": 0,
                            "role_recognition_correct": 0,
                            "role_recognition_total": 0,
                            "metrics": {
                                "role_recognition_accuracy": [],
                                "deception_success_rate": [],
                                "voting_accuracy": [],
                                "communication_effectiveness": [],
                                "survival_rate": [],
                                "ability_usage_accuracy": []
                            }
                        }
                    
                    # 更新统计
                    model_stats[ai_model]["total_games"] += 1
                    if is_winner:
                        model_stats[ai_model]["wins"] += 1
                    
                    if role == "werewolf":
                        model_stats[ai_model]["werewolf_games"] += 1
                        if is_winner:
                            model_stats[ai_model]["werewolf_wins"] += 1
                    else:
                        model_stats[ai_model]["villager_games"] += 1
                        if is_winner:
                            model_stats[ai_model]["villager_wins"] += 1
                    
                    if is_alive:
                        model_stats[ai_model]["survival_count"] += 1
                    
                    # 收集指标数据
                    for metric_name in model_stats[ai_model]["metrics"]:
                        if metric_name in row and row[metric_name]:
                            try:
                                value = float(row[metric_name])
                                model_stats[ai_model]["metrics"][metric_name].append(value)
                            except (ValueError, TypeError):
                                pass
        
        # 创建CSV文件名
        csv_file = f'game_stats/multi_game_stats_{self.timestamp}.csv'
        
        # 写入CSV文件
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                "AI模型", "总场次", "总胜场", "总胜率", 
                "狼人场次", "狼人胜场", "狼人胜率",
                "好人场次", "好人胜场", "好人胜率",
                "存活率", "角色识别准确率", "欺骗成功率", 
                "投票准确率", "沟通效果", "能力使用准确率"
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # 为每个模型写入一行
            for model, stats in model_stats.items():
                # 计算胜率
                win_rate = stats["wins"] / stats["total_games"] if stats["total_games"] > 0 else 0
                werewolf_win_rate = stats["werewolf_wins"] / stats["werewolf_games"] if stats["werewolf_games"] > 0 else 0
                villager_win_rate = stats["villager_wins"] / stats["villager_games"] if stats["villager_games"] > 0 else 0
                survival_rate = stats["survival_count"] / stats["total_games"] if stats["total_games"] > 0 else 0
                
                # 计算平均指标
                avg_metrics = {}
                for metric_name, values in stats["metrics"].items():
                    avg_metrics[metric_name] = sum(values) / len(values) if values else 0
                
                row = {
                    "AI模型": model,
                    "总场次": stats["total_games"],
                    "总胜场": stats["wins"],
                    "总胜率": win_rate,
                    "狼人场次": stats["werewolf_games"],
                    "狼人胜场": stats["werewolf_wins"],
                    "狼人胜率": werewolf_win_rate,
                    "好人场次": stats["villager_games"],
                    "好人胜场": stats["villager_wins"],
                    "好人胜率": villager_win_rate,
                    "存活率": survival_rate,
                    "角色识别准确率": avg_metrics.get("role_recognition_accuracy", 0),
                    "欺骗成功率": avg_metrics.get("deception_success_rate", 0),
                    "投票准确率": avg_metrics.get("voting_accuracy", 0),
                    "沟通效果": avg_metrics.get("communication_effectiveness", 0),
                    "能力使用准确率": avg_metrics.get("ability_usage_accuracy", 0)
                }
                
                writer.writerow(row)
        
        logging.info(f"多轮游戏统计已保存到 {csv_file}")

    def _generate_analysis_report(self):
        """生成分析报告"""
        report_file = f'test_analysis/analysis_report_{self.timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=== 狼人杀游戏分析报告 ===\n\n")
            f.write(f"游戏时间: {self.game_record['start_time']}\n")
            f.write(f"游戏时长: {self.game_record['game_stats']['total_rounds']} 回合\n\n")
            
            # 添加每轮详细记录
            f.write("\n=== 每轮详细记录 ===\n")
            for round_record in self.game_record["round_records"]:
                round_num = round_record["round"]
                f.write(f"\n第 {round_num} 回合\n")
                f.write("-" * 40 + "\n")
                
                # 讨论记录
                if "discussions" in round_record:
                    f.write("\n讨论内容：\n")
                    for disc in round_record["discussions"]:
                        f.write(f"{disc['player']}：\n")
                        f.write(f"{disc['content']}\n")
                
                # 投票记录
                if "vote_results" in round_record:
                    f.write("\n投票结果：\n")
                    vote_results = round_record["vote_results"]
                    for player_id, votes in vote_results["vote_counts"].items():
                        f.write(f"- {vote_results['player_names'][player_id]}: {votes} 票\n")
                        voters = [v["voter_name"] for v in vote_results["vote_details"] if v["target"] == player_id]
                        f.write(f"  投票者: {', '.join(voters)}\n")
                    
                    if vote_results.get("is_tie"):
                        f.write("\n出现平票！\n")
                        f.write(f"平票玩家：{', '.join(vote_results['tied_players'])}\n")
                        f.write(f"随机选择了 {vote_results['voted_out_name']}\n")
                    else:
                        f.write(f"\n投票最高的是 {vote_results['voted_out_name']}，得到 {vote_results['max_votes']} 票\n")
                
                f.write("\n")
            
            # 现有的统计信息
            f.write("\n=== 游戏统计 ===\n")
            f.write(f"- 总死亡数: {self.game_record['game_stats']['total_deaths']}\n")
            f.write(f"- 技能使用次数: {self.game_record['game_stats']['ability_uses']}\n")
            f.write(f"- 投票次数: {len(self.game_record['game_stats']['votes'])}\n")
            
            # 添加投票有效性统计
            if "vote_validity" in self.metrics:
                total_votes = self.metrics["vote_validity"]["total_votes"]
                valid_votes = self.metrics["vote_validity"]["valid_votes"]
                if total_votes > 0:
                    validity_rate = (valid_votes / total_votes) * 100
                    f.write(f"\n投票统计:\n")
                    f.write(f"- 总投票数: {total_votes}\n")
                    f.write(f"- 有效投票数: {valid_votes}\n")
                    f.write(f"- 投票有效率: {validity_rate:.1f}%\n")
                    
                    f.write("\n各玩家投票统计:\n")
                    for player_id, stats in self.metrics["vote_validity"]["player_stats"].items():
                        if stats["total_votes"] > 0:
                            player_validity_rate = (stats["valid_votes"] / stats["total_votes"]) * 100
                            f.write(f"\n玩家 {player_id}:\n")
                            f.write(f"- 投票有效率: {player_validity_rate:.1f}%\n")
                            f.write(f"- 总投票数: {stats['total_votes']}\n")
                            if stats["invalid_reasons"]:
                                f.write("- 无效原因统计:\n")
                                for reason, count in stats["invalid_reasons"].items():
                                    f.write(f"  * {reason}: {count}次\n")
            
            f.write("\n评估指标:\n")
            for metric_name, value in self.game_record["final_result"]["metrics"].items():
                f.write(f"- {metric_name}: {value:.2%}\n")
            
            f.write(f"\n胜利方: {self.game_record['final_result']['winner']}\n")

    def log_round_discussion(self, round_num: int, discussions: List[Dict]):
        """记录每轮的讨论内容
        
        Args:
            round_num: 当前回合数
            discussions: 讨论内容列表，每项包含说话者和内容
        """
        round_record = {
            "round": round_num,
            "phase": "discussion",
            "discussions": discussions,
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加到轮次记录
        self._add_to_round_record(round_num, "discussions", discussions)
        
        # 记录到事件
        self.game_record["events"].append({
            "type": "round_discussion",
            "round": round_num,
            "discussions": discussions,
            "timestamp": datetime.now().isoformat()
        })
        
        # 记录日志
        logging.info(f"\n=== 第 {round_num} 回合讨论记录 ===")
        for disc in discussions:
            logging.info(f"{disc['player']}: {disc['content']}")

    def log_round_vote(self, round_num: int, vote_results: Dict):
        """记录每轮的投票结果
        
        Args:
            round_num: 当前回合数
            vote_results: 投票结果，包含得票情况、投票详情等
        """
        vote_record = {
            "round": round_num,
            "phase": "vote",
            "vote_results": vote_results,
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加到轮次记录
        self._add_to_round_record(round_num, "vote_results", vote_results)
        
        # 记录到事件
        self.game_record["events"].append({
            "type": "round_vote",
            "round": round_num,
            "vote_results": vote_results,
            "timestamp": datetime.now().isoformat()
        })
        
        # 记录日志
        logging.info(f"\n=== 第 {round_num} 回合投票结果 ===")
        logging.info("得票情况：")
        for player_id, votes in vote_results["vote_counts"].items():
            logging.info(f"- {vote_results['player_names'][player_id]}: {votes} 票")
            voters = [v["voter_name"] for v in vote_results["vote_details"] if v["target"] == player_id]
            logging.info(f"  投票者: {', '.join(voters)}")
        
        if vote_results.get("is_tie"):
            logging.info("\n出现平票！")
            logging.info(f"平票玩家：{', '.join(vote_results['tied_players'])}")
            logging.info(f"随机选择了 {vote_results['voted_out_name']}")
        else:
            logging.info(f"\n投票最高的是 {vote_results['voted_out_name']}，得到 {vote_results['max_votes']} 票")

    def _add_to_round_record(self, round_num: int, record_type: str, data: Any):
        """添加数据到轮次记录
        
        Args:
            round_num: 当前回合数
            record_type: 记录类型（discussions/vote_results）
            data: 要记录的数据
        """
        # 查找当前回合的记录
        round_record = None
        for record in self.game_record["round_records"]:
            if record["round"] == round_num:
                round_record = record
                break
        
        # 如果没有找到，创建新的回合记录
        if round_record is None:
            round_record = {
                "round": round_num,
                "timestamp": datetime.now().isoformat()
            }
            self.game_record["round_records"].append(round_record)
        
        # 添加数据
        round_record[record_type] = data

def setup_logger(debug: bool = False) -> GameLogger:
    """创建并返回游戏日志记录器"""
    return GameLogger(debug) 