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
        }
    }

def update_statistics(statistics: dict, game_result: dict):
    """更新统计数据"""
    statistics["total_games"] += 1
    
    # 更新胜负统计
    if game_result["winner"] == "狼人阵营":
        statistics["werewolf_wins"] += 1
    else:
        statistics["villager_wins"] += 1
    
    # 更新模型统计
    for player_id, player_data in game_result["final_state"]["players"].items():
        model_type = player_data["ai_type"]
        if model_type not in statistics["model_stats"]:
            statistics["model_stats"][model_type] = {
                "games": 0,
                "wins": 0,
                "metrics": initialize_statistics()["metrics"].copy()
            }
        
        statistics["model_stats"][model_type]["games"] += 1
        if (game_result["winner"] == "狼人阵营" and player_data["role"] == "werewolf") or \
           (game_result["winner"] == "好人阵营" and player_data["role"] != "werewolf"):
            statistics["model_stats"][model_type]["wins"] += 1
    
    # 更新角色统计
    for player_id, player_data in game_result["final_state"]["players"].items():
        role = player_data["role"]
        statistics["role_stats"][role]["total"] += 1
        if (game_result["winner"] == "狼人阵营" and role == "werewolf") or \
           (game_result["winner"] == "好人阵营" and role != "werewolf"):
            statistics["role_stats"][role]["wins"] += 1
    
    # 更新评估指标
    if "metrics" in game_result:
        for metric_name, value in game_result["metrics"].items():
            if metric_name in statistics["metrics"]:
                statistics["metrics"][metric_name].append(value)

def print_statistics(statistics: dict):
    """打印统计结果"""
    print("\n=== 游戏统计 ===")
    print(f"总场次: {statistics['total_games']}")
    print(f"狼人胜率: {statistics['werewolf_wins']/statistics['total_games']:.2%}")
    print(f"好人胜率: {statistics['villager_wins']/statistics['total_games']:.2%}")
    
    print("\n各角色胜率:")
    for role, stats in statistics["role_stats"].items():
        if stats["total"] > 0:
            win_rate = stats["wins"] / stats["total"]
            print(f"{role}: {win_rate:.2%} ({stats['wins']}/{stats['total']})")
    
    print("\n各模型表现:")
    for model, stats in statistics["model_stats"].items():
        if stats["games"] > 0:
            win_rate = stats["wins"] / stats["games"]
            print(f"{model}: 胜率 {win_rate:.2%} ({stats['wins']}/{stats['games']})")
    
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
                # 合并配置
                game_config = {
                    "roles": role_config["roles"],
                    "game_settings": role_config["game_settings"],
                    "ai_players": ai_config["ai_players"],
                    "delay": args.delay,
                    "total_rounds": args.rounds  # 添加总轮数配置
                }
                
                # 创建游戏实例
                logger.info(f"正在初始化第 {round_num + 1} 轮游戏...")
                game = GameController(game_config)
                
                # 运行游戏
                print(f"\n=== 第 {round_num + 1}/{args.rounds} 轮游戏开始 ===\n")
                logger.info("游戏开始...")
                
                # 同步运行游戏
                game.run_game()
                
                # 获取游戏结果并更新统计
                game_result = game.game_state
                update_statistics(statistics, game_result)
                
                # 每轮结束后保存断点
                save_checkpoint(round_num + 1, statistics)
                
                print(f"\n=== 第 {round_num + 1} 轮游戏结束 ===\n")
                logger.info("游戏结束")
                
            except KeyboardInterrupt:
                print("\n游戏被用户中断")
                logger.info(f"游戏在第 {round_num + 1} 轮被用户中断")
                save_checkpoint(round_num, statistics)
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