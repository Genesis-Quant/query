"""复用调用方的 Loguru 配置，不移除 sink、不更改日志格式。"""

from loguru import logger

__all__ = ["logger"]
