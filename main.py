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
    return parser.parse_args()

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
            
        # 合并配置
        game_config = {
            "roles": role_config["roles"],
            "game_settings": role_config["game_settings"],
            "ai_players": ai_config["ai_players"],
            "delay": args.delay  # 添加延迟设置
        }
        
        # 创建游戏实例
        logger.info("正在初始化游戏...")
        game = GameController(game_config)
        
        # 运行游戏
        print("\n=== 游戏开始 ===\n")
        logger.info("游戏开始...")
        
        # 同步运行游戏
        game.run_game()
        
        print("\n=== 游戏结束 ===\n")
        logger.info("游戏结束")
        
    except FileNotFoundError as e:
        logger.error(f"配置文件不存在: {str(e)}")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f"配置文件格式错误: {str(e)}")
        return 1
    except KeyboardInterrupt:
        print("\n游戏被用户中断")
        logger.info("游戏被用户中断")
        return 0
    except Exception as e:
        logger.error(f"游戏运行出错: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 