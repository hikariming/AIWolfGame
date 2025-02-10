"""
日志记录器，负责记录游戏过程中的所有信息

主要职责：
1. 日志记录
   - 记录游戏流程
   - 记录玩家行为
   - 记录 AI 响应
   - 记录系统事件

2. 日志格式化
   - 控制台输出格式
   - 文件记录格式
   - 不同级别日志区分

3. 与其他模块的交互：
   - 被所有模块调用记录日志
   - 管理 logs 目录
   - 支持日志回放功能

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
            "final_result": None
        }
        self._setup_logger()

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
        self.game_record["final_result"] = {
            "winner": winner,
            "final_state": final_state,
            "end_time": datetime.now().isoformat()
        }
        self.save_game_record()

    def save_game_record(self):
        """保存完整的游戏记录"""
        record_file = f'logs/game_record_{self.timestamp}.json'
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(self.game_record, f, ensure_ascii=False, indent=2)

def setup_logger(debug: bool = False) -> GameLogger:
    """创建并返回游戏日志记录器"""
    return GameLogger(debug) 