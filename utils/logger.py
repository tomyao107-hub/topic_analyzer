"""
日志工具
支持文件日志和 GUI 信号输出
"""
import logging
import os
from datetime import datetime
try:
    from PySide6.QtCore import QObject, Signal

    class LogSignals(QObject):
        """日志信号，用于将日志消息传递给 GUI。"""
        message = Signal(str, str)   # (level, message)
except ImportError:
    class _NullSignal:
        def emit(self, *_args):
            return None

        def connect(self, *_args):
            return None

    class LogSignals:
        """Headless bridge replacement when PySide6 is not bundled."""
        def __init__(self):
            self.message = _NullSignal()


# 全局信号实例
log_signals = LogSignals()


class GUIHandler(logging.Handler):
    """将日志记录发送到 GUI 信号的 Handler"""

    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname
            log_signals.message.emit(level, msg)
        except Exception:
            pass


def setup_logger(log_dir: str = "") -> logging.Logger:
    """初始化应用日志系统"""
    logger = logging.getLogger("topic_analyzer")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    # 控制台 Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # GUI Handler
    gh = GUIHandler()
    gh.setLevel(logging.DEBUG)
    gh.setFormatter(fmt)
    logger.addHandler(gh)

    # 文件 Handler（如果提供了目录）
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("topic_analyzer")
