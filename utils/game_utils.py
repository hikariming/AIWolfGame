"""
游戏通用工具函数集合

主要功能：
1. 配置文件处理
   - 读取 JSON 配置
   - 验证配置有效性
   - 合并默认配置

2. 游戏辅助功能
   - 随机角色分配
   - 计算投票结果
   - 游戏状态检查
   - 定时器实现

3. 与其他模块的交互：
   - 被 game_controller.py 调用使用工具函数
   - 被 ai_players.py 使用配置处理
   - 提供通用异常处理

函数列表：
def load_config()
def validate_config()
def assign_roles()
def calculate_votes()
def create_timer()
def handle_exceptions()
""" 

import json
from typing import Dict, Any, List
import logging
import random

def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载配置文件失败: {str(e)}")
        raise

def validate_game_config(config: Dict[str, Any]) -> bool:
    """验证游戏配置是否有效"""
    try:
        # 检查必要的配置项
        required_keys = ["game_settings", "roles"]
        if not all(key in config for key in required_keys):
            return False
            
        # 检查角色配置
        roles = config["roles"]
        if not all(key in roles for key in ["werewolf", "villager"]):
            return False
            
        # 检查玩家数量是否合理
        total_players = sum(len(players) for players in roles.values())
        if total_players < 3:  # 至少需要3个玩家
            return False
            
        # 检查狼人数量是否合理
        werewolf_count = len(roles.get("werewolf", []))
        if werewolf_count == 0 or werewolf_count >= total_players / 2:
            return False
        
        # 检查多轮分配配置（如果存在）
        if "multi_round_assignments" in config:
            assignments = config["multi_round_assignments"]
            
            # 检查是否为列表
            if not isinstance(assignments, list):
                logging.error("multi_round_assignments 必须是一个列表")
                return False
                
            # 获取所有角色ID
            all_role_ids = []
            for role_type, role_dict in roles.items():
                all_role_ids.extend(role_dict.keys())
                
            # 检查每个轮次的配置
            for round_config in assignments:
                # 检查必要的字段
                if not all(key in round_config for key in ["round", "assignments"]):
                    logging.error(f"轮次配置缺少必要字段: {round_config}")
                    return False
                    
                # 检查轮次是否为正整数
                if not isinstance(round_config["round"], int) or round_config["round"] <= 0:
                    logging.error(f"轮次必须是正整数: {round_config['round']}")
                    return False
                    
                # 检查分配是否包含所有角色
                if set(round_config["assignments"].keys()) != set(all_role_ids):
                    logging.error(f"轮次 {round_config['round']} 的角色分配不完整")
                    return False
            
        return True
    except Exception as e:
        logging.error(f"配置验证失败: {str(e)}")
        return False

def format_game_state(game_state: Dict[str, Any]) -> str:
    """格式化游戏状态信息，用于显示和日志"""
    output = []
    output.append(f"第 {game_state['current_round']} 回合")
    output.append(f"当前阶段: {'夜晚' if game_state['phase'] == 'night' else '白天'}")
    
    # 存活玩家信息
    alive_players = [
        f"{info['name']}({pid})" 
        for pid, info in game_state['players'].items() 
        if info['is_alive']
    ]
    output.append(f"存活玩家: {', '.join(alive_players)}")
    
    # 统计信息
    output.append(f"存活狼人: {game_state['alive_count']['werewolf']}")
    output.append(f"存活好人: {game_state['alive_count']['villager']}")
    
    return "\n".join(output)

def get_random_target(players: List[str], exclude: List[str] = None) -> str:
    """随机选择一个目标（用于AI决策失败时的后备方案）"""
    valid_targets = [p for p in players if p not in (exclude or [])]
    return random.choice(valid_targets) if valid_targets else "" 