"""
环境变量加载工具

主要功能：
1. 从.env文件加载环境变量
2. 提供获取各类API密钥的函数
3. 支持默认值和错误处理
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

def load_env_vars(env_file: str = ".env") -> bool:
    """加载环境变量
    
    Args:
        env_file: 环境变量文件路径，默认为项目根目录下的.env
        
    Returns:
        bool: 是否成功加载
    """
    env_path = PROJECT_ROOT / env_file
    if not env_path.exists():
        logging.warning(f"环境变量文件 {env_path} 不存在")
        return False
    
    load_dotenv(dotenv_path=env_path)
    logging.info(f"已从 {env_path} 加载环境变量")
    return True

def get_api_key(provider: str) -> Optional[str]:
    """获取指定提供商的API密钥
    
    Args:
        provider: API提供商名称，如openai, anthropic, google等
        
    Returns:
        Optional[str]: API密钥，如果未配置则返回None
    """
    key_mapping = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "gemini": "GOOGLE_API_KEY",  # 别名
        "deepseek": "DEEPSEEK_API_KEY",
        # 可以添加更多映射
    }
    
    if provider.lower() not in key_mapping:
        logging.error(f"未知的API提供商: {provider}")
        return None
    
    env_key = key_mapping[provider.lower()]
    api_key = os.getenv(env_key)
    
    if not api_key:
        logging.warning(f"未设置 {env_key} 环境变量")
    
    return api_key

def get_base_url(provider: str) -> Optional[str]:
    """获取指定提供商的API基础URL
    
    Args:
        provider: API提供商名称，如openai, anthropic等
        
    Returns:
        Optional[str]: API基础URL，如果未配置则返回None
    """
    url_mapping = {
        "openai": "OPENAI_BASE_URL",
        "deepseek": "DEEPSEEK_BASE_URL"
        # 可以添加更多映射
    }
    
    if provider.lower() not in url_mapping:
        return None
    
    env_key = url_mapping[provider.lower()]
    base_url = os.getenv(env_key)
    
    return base_url

def get_game_settings() -> Dict[str, Any]:
    """获取游戏配置
    
    Returns:
        Dict[str, Any]: 游戏配置字典
    """
    return {
        "debug": os.getenv("DEBUG_MODE", "false").lower() == "true",
        "export_path": os.getenv("EXPORT_PATH", "./analysis"),
        "rounds": int(os.getenv("DEFAULT_ROUNDS", "100")),
        "delay": float(os.getenv("DEFAULT_DELAY", "1.0")),
    }

def load_api_config() -> Dict[str, Dict[str, str]]:
    """加载所有API配置
    
    Returns:
        Dict[str, Dict[str, str]]: API配置字典
    """
    providers = ["openai", "anthropic", "google", "deepseek"]
    config = {}
    
    for provider in providers:
        api_key = get_api_key(provider)
        if api_key:
            config[provider] = {"api_key": api_key}
            
            # 添加base_url（如果有）
            base_url = get_base_url(provider)
            if base_url:
                config[provider]["base_url"] = base_url
    
    return config

# 初始化
load_env_vars() 