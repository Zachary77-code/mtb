"""
日志配置
"""
import sys
from pathlib import Path

from loguru import logger

from config.settings import LOGS_DIR


def setup_logger(
    log_level: str = "INFO",
    log_file: str = "mtb.log",
    console: bool = True
) -> logger:
    """
    配置日志

    Args:
        log_level: 日志级别
        log_file: 日志文件名
        console: 是否输出到控制台

    Returns:
        配置后的 logger
    """
    # 移除默认处理器
    logger.remove()

    # 日志格式
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    simple_format = (
        "{time:HH:mm:ss} | {level: <8} | {message}"
    )

    # 控制台输出
    if console:
        logger.add(
            sys.stdout,
            format=simple_format,
            level=log_level,
            colorize=True
        )

    # 文件输出
    log_path = LOGS_DIR / log_file
    logger.add(
        str(log_path),
        format=log_format,
        level=log_level,
        rotation="10 MB",  # 文件大小达到 10MB 时轮转
        retention="7 days",  # 保留 7 天
        compression="zip",  # 压缩旧日志
        encoding="utf-8"
    )

    return logger


# 默认配置
mtb_logger = setup_logger()


if __name__ == "__main__":
    # 测试日志
    mtb_logger.info("日志模块测试")
    mtb_logger.debug("调试信息")
    mtb_logger.warning("警告信息")
    mtb_logger.error("错误信息")
    print(f"日志文件位置: {LOGS_DIR}")
