"""
配置模块

该模块负责管理项目的配置信息，包括 jAccount 登录凭据、API 密钥等。
"""

from pathlib import Path

# 默认配置目录
CONFIG_DIR = Path(__file__).parent.absolute()

# jAccount 配置文件路径
JACCOUNT_CONFIG_PATH = CONFIG_DIR / "jaccount_config.json"

__all__ = ["CONFIG_DIR", "JACCOUNT_CONFIG_PATH"]
