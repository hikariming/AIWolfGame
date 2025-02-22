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
            "model_metrics": {}  # 新增：模型评估指标
        }
        self._setup_logger()
        self._init_metrics()

    def _setup_logger(self):
        """设置日志系统"""
        # 创建logs目录
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # 设置日志文件名
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'logs/game_{self.timestamp}.log'
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 设置文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # 设置控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

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
        logging.debug(f"角色识别: 玩家{player_id} {'正确' if is_correct else '错误'}")

    def log_deception_attempt(self, player_id: str, is_successful: bool):
        """记录欺骗成功率"""
        self.metrics["deception_success"]["attempts"] += 1
        if is_successful:
            self.metrics["deception_success"]["successful"] += 1
        logging.debug(f"欺骗尝试: 玩家{player_id} {'成功' if is_successful else '失败'}")

    def log_vote(self, voter_id: str, target_id: str, is_correct: bool):
        """记录投票准确率"""
        self.metrics["voting_accuracy"]["total"] += 1
        if is_correct:
            self.metrics["voting_accuracy"]["correct"] += 1
        logging.debug(f"投票: 玩家{voter_id}投给{target_id} {'正确' if is_correct else '错误'}")

    def log_communication(self, player_id: str, message_id: str, influenced_others: bool):
        """记录沟通效果"""
        self.metrics["communication_effect"]["total_messages"] += 1
        if influenced_others:
            self.metrics["communication_effect"]["influential_messages"] += 1
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
        logging.debug(f"能力使用: 玩家{player_id}使用{ability_type} {'正确' if is_correct else '错误'}")

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
        self.game_record["rounds"].append({
            "round_number": round_num,
            "phase": phase,
            "events": events
        })

    def log_event(self, event_type: str, details: Dict[str, Any]):
        """记录游戏事件"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            **details
        }
        self.game_record["events"].append(event)
        logging.info(f"游戏事件: {event_type} - {details}")

    def log_game_over(self, winner: str, final_state: Dict[str, Any]):
        """记录游戏结束信息"""
        metrics = self.calculate_metrics()
        self.game_record["final_result"] = {
            "winner": winner,
            "final_state": final_state,
            "end_time": datetime.now().isoformat(),
            "metrics": metrics  # 添加评估指标到最终结果
        }
        
        # 记录评估指标
        logging.info("游戏评估指标:")
        for metric_name, value in metrics.items():
            logging.info(f"{metric_name}: {value:.2%}")
            
        self.save_game_record()

    def save_game_record(self):
        """保存完整的游戏记录"""
        record_file = f'logs/game_record_{self.timestamp}.json'
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(self.game_record, f, ensure_ascii=False, indent=2)

def setup_logger(debug: bool = False) -> GameLogger:
    """创建并返回游戏日志记录器"""
    return GameLogger(debug) 