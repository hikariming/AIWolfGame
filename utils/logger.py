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
            }
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

    def _generate_analysis_report(self):
        """生成分析报告"""
        report_file = f'test_analysis/analysis_report_{self.timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=== 狼人杀游戏分析报告 ===\n\n")
            f.write(f"游戏时间: {self.game_record['start_time']}\n")
            f.write(f"游戏时长: {self.game_record['game_stats']['total_rounds']} 回合\n\n")
            
            f.write("游戏统计:\n")
            f.write(f"- 总死亡数: {self.game_record['game_stats']['total_deaths']}\n")
            f.write(f"- 技能使用次数: {self.game_record['game_stats']['ability_uses']}\n")
            f.write(f"- 投票次数: {len(self.game_record['game_stats']['votes'])}\n\n")
            
            f.write("评估指标:\n")
            for metric_name, value in self.game_record["final_result"]["metrics"].items():
                f.write(f"- {metric_name}: {value:.2%}\n")
            
            f.write(f"\n胜利方: {self.game_record['final_result']['winner']}\n")

def setup_logger(debug: bool = False) -> GameLogger:
    """创建并返回游戏日志记录器"""
    return GameLogger(debug) 