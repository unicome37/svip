"""
SVIP v1.0 — Logging Infrastructure

统一日志系统，替代 print() 输出。
支持按级别过滤，格式化输出。
"""
import logging
import sys
from config.settings import settings


def get_logger(name: str = "svip") -> logging.Logger:
    """获取 SVIP 日志器"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    return logger
