"""
游戏程序入口

主要职责：
1. 程序初始化
   - 解析命令行参数
   - 加载配置文件
   - 初始化日志系统
   - 创建游戏实例

2. 游戏运行控制
   - 启动游戏
   - 异常处理
   - 程序退出处理
   - 断点续玩功能
   - 多轮游戏统计

3. 与其他模块的交互：
   - 创建 GameController 实例
   - 使用 utils 中的工具函数
   - 调用 logger 记录主程序日志

主要流程：
if __name__ == "__main__":
    # 解析命令行参数
    # 加载配置
    # 初始化日志
    # 创建游戏实例
    # 运行游戏
    # 处理退出
""" 

import argparse
import json
import logging
import sys
import os
from pathlib import Path
from game.game_controller import GameController
from utils.logger import setup_logger
from utils.game_utils import load_config, validate_game_config
from typing import List, Dict
import copy
import csv
from datetime import datetime

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='AI狼人杀模拟器')
    parser.add_argument('--role-config', type=str, default='config/role_config.json', 
                      help='角色配置文件路径')
    parser.add_argument('--ai-config', type=str, default='config/ai_config.json',
                      help='AI配置文件路径')
    parser.add_argument('--debug', action='store_true', help='是否启用调试模式')
    parser.add_argument('--delay', type=float, default=1.0,
                      help='每个动作之间的延迟时间(秒)')
    parser.add_argument('--rounds', type=int, default=100,
                      help='要运行的游戏轮数(默认100轮)')
    parser.add_argument('--resume', action='store_true',
                      help='是否从上次中断处继续游戏')
    parser.add_argument('--export-path', type=str, default='analysis',
                      help='评测数据导出路径')
    return parser.parse_args()

def load_checkpoint():
    """加载游戏断点数据"""
    checkpoint_file = 'logs/checkpoint.json'
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载断点数据失败: {str(e)}")
    return None

def save_checkpoint(completed_rounds: int, statistics: dict):
    """保存游戏断点数据"""
    checkpoint_file = 'logs/checkpoint.json'
    try:
        checkpoint_data = {
            "completed_rounds": completed_rounds,
            "statistics": statistics
        }
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存断点数据失败: {str(e)}")

def initialize_statistics():
    """初始化统计数据"""
    return {
        "total_games": 0,
        "werewolf_wins": 0,
        "villager_wins": 0,
        "model_stats": {},  # 每个模型的详细统计
        "role_stats": {     # 每个角色的表现统计
            "werewolf": {"wins": 0, "total": 0},
            "villager": {"wins": 0, "total": 0},
            "seer": {"wins": 0, "total": 0},
            "witch": {"wins": 0, "total": 0},
            "hunter": {"wins": 0, "total": 0}
        },
        "metrics": {        # 评估指标统计
            "role_recognition_accuracy": [],
            "deception_success_rate": [],
            "voting_accuracy": [],
            "communication_effectiveness": [],
            "survival_rate": [],
            "ability_usage_accuracy": []
        },
        "role_assignments": [],  # 记录每轮的角色分配
        "model_performance": {},  # 每个模型在不同角色下的表现
        "game_details": []  # 每局游戏的详细信息
    }

def assign_models_to_roles(models: List[str], roles: Dict, round_num: int, interval: int) -> Dict:
    """根据轮次分配模型到角色
    
    Args:
        models: 待评估的模型列表
        roles: 角色配置
        round_num: 当前轮次
        interval: 角色轮换间隔
        
    Returns:
        Dict: 角色到模型的映射
    """
    # 计算当前轮次的轮换次数
    rotation = (round_num // interval) % len(models)
    
    # 获取所有角色ID
    all_roles = []
    for role_type, role_dict in roles.items():
        for role_id in role_dict.keys():
            all_roles.append(role_id)
    
    # 根据轮换次数调整模型顺序
    rotated_models = models[rotation:] + models[:rotation]
    
    # 分配模型到角色
    assignments = {}
    for i, role_id in enumerate(all_roles):
        model_index = i % len(rotated_models)
        assignments[role_id] = rotated_models[model_index]
    
    return assignments

def get_model_assignments_from_config(config: Dict, round_num: int) -> Dict:
    """从配置文件中获取指定轮次的角色分配
    
    Args:
        config: 游戏配置
        round_num: 当前轮次（从0开始）
        
    Returns:
        Dict: 角色到模型的映射
    """
    # 检查配置文件中是否有多轮分配配置
    if "multi_round_assignments" not in config:
        # 如果没有多轮分配配置，使用原来的随机分配逻辑
        return assign_models_to_roles(
            config.get("models_to_evaluate", []),
            config["roles"],
            round_num,
            config["game_settings"]["role_rotation_interval"]
        )
    
    # 获取多轮分配配置
    assignments_config = config["multi_round_assignments"]
    
    # 计算实际轮次（从1开始）
    actual_round = round_num + 1
    
    # 查找对应轮次的分配配置
    for round_config in assignments_config:
        if round_config["round"] == actual_round:
            return round_config["assignments"]
    
    # 如果找不到对应轮次的配置，使用最后一个配置的轮次模数
    if assignments_config:
        max_configured_round = max(cfg["round"] for cfg in assignments_config)
        for round_config in assignments_config:
            if round_config["round"] == (actual_round - 1) % max_configured_round + 1:
                return round_config["assignments"]
    
    # 如果仍然找不到，使用原来的随机分配逻辑
    return assign_models_to_roles(
        config.get("models_to_evaluate", []),
        config["roles"],
        round_num,
        config["game_settings"]["role_rotation_interval"]
    )

def export_analysis(statistics: dict, config: dict, export_path: str):
    """导出分析数据
    
    Args:
        statistics: 统计数据
        config: AI配置
        export_path: 导出路径
    """
    os.makedirs(export_path, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 导出JSON格式
    if "json" in config["evaluation_settings"]["export_format"]:
        json_path = os.path.join(export_path, f'analysis_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, ensure_ascii=False, indent=2)
    
    # 导出CSV格式
    if "csv" in config["evaluation_settings"]["export_format"]:
        # 模型总体表现
        model_performance_path = os.path.join(export_path, f'model_performance_{timestamp}.csv')
        with open(model_performance_path, 'w', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Model', 'Games', 'Wins', 'Win Rate'] + list(statistics["metrics"].keys()))
            for model, stats in statistics["model_stats"].items():
                metrics = [sum(stats["metrics"][m])/len(stats["metrics"][m]) if stats["metrics"][m] else 0 
                          for m in statistics["metrics"].keys()]
                writer.writerow([
                    model,
                    stats["games"],
                    stats["wins"],
                    stats["wins"]/stats["games"] if stats["games"] > 0 else 0
                ] + metrics)
        
        # 角色表现
        role_performance_path = os.path.join(export_path, f'role_performance_{timestamp}.csv')
        with open(role_performance_path, 'w', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Role', 'Games', 'Wins', 'Win Rate'])
            for role, stats in statistics["role_stats"].items():
                if stats["total"] > 0:
                    writer.writerow([
                        role,
                        stats["total"],
                        stats["wins"],
                        stats["wins"]/stats["total"]
                    ])
        
        # 详细游戏记录
        game_details_path = os.path.join(export_path, f'game_details_{timestamp}.csv')
        with open(game_details_path, 'w', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Game ID', 'Round', 'Winner', 'Duration',
                'Wolf Models', 'Village Models', 'Special Role Models',
                'Key Events'
            ])
            for game in statistics["game_details"]:
                writer.writerow([
                    game["game_id"],
                    game["round"],
                    game["winner"],
                    game["duration"],
                    "|".join(game["wolf_models"]),
                    "|".join(game["village_models"]),
                    "|".join(game["special_role_models"]),
                    "|".join(game["key_events"])
                ])

def update_statistics(statistics: dict, game_result: dict, model_assignments: dict):
    """更新统计数据"""
    statistics["total_games"] += 1
    game_id = f"game_{statistics['total_games']}"
    
    # 确保winner字段存在并处理
    winner = game_result.get("winner", "未知")
    if winner == "好人阵营":
        statistics["villager_wins"] += 1
    elif winner == "狼人阵营":
        statistics["werewolf_wins"] += 1
    else:
        # 如果winner字段不存在或为其他值，尝试从final_result中获取
        if "final_result" in game_result and "winner" in game_result["final_result"]:
            winner = game_result["final_result"]["winner"]
            if winner == "好人阵营":
                statistics["villager_wins"] += 1
            elif winner == "狼人阵营":
                statistics["werewolf_wins"] += 1
    
    # 记录本局详细信息
    game_detail = {
        "game_id": game_id,
        "round": game_result.get("current_round", 0),
        "winner": winner,
        "duration": 0,  # 默认值
        "wolf_models": [],
        "village_models": [],
        "special_role_models": [],
        "key_events": [],
        "model_assignments": model_assignments  # 记录本轮的角色分配
    }
    
    # 计算游戏时长
    if "start_time" in game_result and "final_result" in game_result and "end_time" in game_result["final_result"]:
        try:
            start_time = datetime.fromisoformat(game_result["start_time"])
            end_time = datetime.fromisoformat(game_result["final_result"]["end_time"])
            game_detail["duration"] = (end_time - start_time).total_seconds()
        except Exception as e:
            logging.error(f"计算游戏时长出错: {str(e)}")
    
    # 提取指标数据，从final_result中的metrics字段获取
    metrics_data = {}
    if "final_result" in game_result and "metrics" in game_result["final_result"]:
        metrics_data = game_result["final_result"]["metrics"]
    
    # 更新模型统计
    if "final_state" in game_result and "players" in game_result["final_state"]:
        for player_id, player_data in game_result["final_state"]["players"].items():
            model_type = model_assignments.get(player_id, "unknown")
            role = player_data.get("role", "unknown")
            
            # 更新模型在不同角色下的表现
            if model_type not in statistics["model_performance"]:
                statistics["model_performance"][model_type] = {
                    role_type: {"games": 0, "wins": 0} 
                    for role_type in ["werewolf", "villager", "seer", "witch", "hunter"]
                }
            
            if role in statistics["model_performance"][model_type]:
                statistics["model_performance"][model_type][role]["games"] += 1
                if (winner == "狼人阵营" and role == "werewolf") or \
                   (winner == "好人阵营" and role != "werewolf"):
                    statistics["model_performance"][model_type][role]["wins"] += 1
            
            # 更新model_stats数据结构
            if model_type not in statistics["model_stats"]:
                statistics["model_stats"][model_type] = {
                    "games": 0,
                    "wins": 0,
                    "metrics": {metric: [] for metric in statistics["metrics"]}
                }
            
            statistics["model_stats"][model_type]["games"] += 1
            if (winner == "狼人阵营" and role == "werewolf") or \
               (winner == "好人阵营" and role != "werewolf"):
                statistics["model_stats"][model_type]["wins"] += 1
                
            # 如果存在指标数据，更新到对应模型的指标中
            for metric_name, value in metrics_data.items():
                if metric_name in statistics["metrics"]:
                    if model_type in statistics["model_stats"]:
                        if metric_name in statistics["model_stats"][model_type]["metrics"]:
                            statistics["model_stats"][model_type]["metrics"][metric_name].append(value)
            
            # 更新游戏详情
            if role == "werewolf":
                game_detail["wolf_models"].append(model_type)
            elif role in ["seer", "witch", "hunter"]:
                game_detail["special_role_models"].append(f"{role}:{model_type}")
            else:
                game_detail["village_models"].append(model_type)
    
    # 记录关键事件
    if "history" in game_result:
        for event in game_result["history"]:
            if isinstance(event, dict) and "event" in event and event["event"] in ["death", "wolf_identify", "seer_check", "witch_action"]:
                game_detail["key_events"].append(f"{event.get('round', 0)}_{event['event']}")
    
    statistics["game_details"].append(game_detail)
    
    # 更新角色统计
    if "final_state" in game_result and "players" in game_result["final_state"]:
        for player_id, player_data in game_result["final_state"]["players"].items():
            role = player_data.get("role", "unknown")
            if role in statistics["role_stats"]:
                statistics["role_stats"][role]["total"] += 1
                if (winner == "狼人阵营" and role == "werewolf") or \
                   (winner == "好人阵营" and role != "werewolf"):
                    statistics["role_stats"][role]["wins"] += 1
    
    # 更新评估指标
    for metric_name, value in metrics_data.items():
        if metric_name in statistics["metrics"]:
            statistics["metrics"][metric_name].append(value)
    
    # 记录角色分配情况
    statistics["role_assignments"].append({
        "game_id": game_id,
        "round_num": statistics["total_games"],
        "assignments": model_assignments
    })

def print_statistics(statistics: dict):
    """打印统计结果"""
    print("\n=== 游戏统计 ===")
    print(f"总场次: {statistics['total_games']}")
    
    # 添加除零保护
    if statistics['total_games'] > 0:
        print(f"狼人胜率: {statistics['werewolf_wins']/statistics['total_games']:.2%}")
        print(f"好人胜率: {statistics['villager_wins']/statistics['total_games']:.2%}")
    else:
        print("狼人胜率: 0.00%")
        print("好人胜率: 0.00%")
    
    print("\n各角色胜率:")
    has_role_stats = False
    for role, stats in statistics["role_stats"].items():
        if stats["total"] > 0:
            has_role_stats = True
            win_rate = stats["wins"] / stats["total"]
            print(f"{role}: {win_rate:.2%} ({stats['wins']}/{stats['total']})")
    if not has_role_stats:
        print("暂无角色胜率数据")
    
    print("\n各模型表现:")
    has_model_stats = False
    for model, stats in statistics["model_stats"].items():
        if stats["games"] > 0:
            has_model_stats = True
            win_rate = stats["wins"] / stats["games"]
            print(f"{model}: 胜率 {win_rate:.2%} ({stats['wins']}/{stats['games']})")
    if not has_model_stats:
        print("暂无模型表现数据")
    
    print("\n评估指标平均值:")
    for metric_name, values in statistics["metrics"].items():
        if values:
            avg_value = sum(values) / len(values)
            print(f"{metric_name}: {avg_value:.2%}")

def main():
    # 解析命令行参数
    args = parse_args()
    
    # 初始化日志系统
    setup_logger(debug=args.debug)
    logger = logging.getLogger(__name__)
    
    try:
        # 加载配置文件
        logger.info("正在加载配置文件...")
        role_config = load_config(args.role_config)
        ai_config = load_config(args.ai_config)
        
        # 验证配置
        if not validate_game_config(role_config):
            logger.error("角色配置文件验证失败")
            return 1
        
        # 获取要评估的模型列表
        models_to_evaluate = ai_config["evaluation_settings"]["models_to_evaluate"]
        role_rotation_interval = role_config["game_settings"]["role_rotation_interval"]
        
        # 初始化或加载统计数据
        statistics = initialize_statistics()
        start_round = 0
        
        if args.resume:
            checkpoint = load_checkpoint()
            if checkpoint:
                start_round = checkpoint["completed_rounds"]
                statistics = checkpoint["statistics"]
                logger.info(f"从第 {start_round + 1} 轮继续游戏")
            else:
                logger.warning("未找到断点数据，从头开始游戏")
        
        # 运行指定轮数的游戏
        for round_num in range(start_round, args.rounds):
            try:
                # 分配模型到角色
                model_assignments = get_model_assignments_from_config(role_config, round_num)
                
                # 更新角色配置中的AI类型
                game_roles = copy.deepcopy(role_config["roles"])
                for role_type, roles in game_roles.items():
                    for role_id in roles:
                        roles[role_id]["ai_type"] = model_assignments[role_id]
                
                # 合并配置
                game_config = {
                    "roles": game_roles,
                    "game_settings": role_config["game_settings"],
                    "ai_players": ai_config["ai_players"],
                    "delay": args.delay,
                    "total_rounds": args.rounds
                }
                
                # 创建游戏实例
                logger.info(f"正在初始化第 {round_num + 1} 轮游戏...")
                game = GameController(game_config)
                
                # 运行游戏
                print(f"\n=== 第 {round_num + 1}/{args.rounds} 轮游戏开始 ===")
                print("本轮角色分配:")
                for role_id, model in model_assignments.items():
                    print(f"{role_id}: {model}")
                print("\n")
                
                logger.info("游戏开始...")
                game.run_game()
                
                # 获取游戏结果并更新统计
                game_result = game.game_state
                update_statistics(statistics, game_result, model_assignments)
                
                # 每轮结束后保存断点和导出分析
                save_checkpoint(round_num + 1, statistics)
                export_analysis(statistics, ai_config, args.export_path)
                
                print(f"\n=== 第 {round_num + 1} 轮游戏结束 ===\n")
                logger.info("游戏结束")
                
            except KeyboardInterrupt:
                print("\n游戏被用户中断")
                logger.info(f"游戏在第 {round_num + 1} 轮被用户中断")
                save_checkpoint(round_num, statistics)
                export_analysis(statistics, ai_config, args.export_path)
                print_statistics(statistics)
                return 0
            except Exception as e:
                logger.error(f"第 {round_num + 1} 轮游戏运行出错: {str(e)}", exc_info=True)
                save_checkpoint(round_num, statistics)
                continue
        
        # 打印最终统计结果
        print_statistics(statistics)
        
    except FileNotFoundError as e:
        logger.error(f"配置文件不存在: {str(e)}")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f"配置文件格式错误: {str(e)}")
        return 1
    except Exception as e:
        logger.error(f"游戏运行出错: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 