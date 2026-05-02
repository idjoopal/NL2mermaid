"""
MCP Server Logger

stdout으로 JSON 형식의 로그를 출력하는 로거를 제공합니다.
"""
import json
import logging
import sys
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """로그를 JSON 형식으로 포맷팅하는 Formatter"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "levelno": record.levelno,
            "name": record.name,
            "message": record.getMessage(),
            "source": {
                "function": record.funcName,
                "line": record.lineno,
                "pathname": record.pathname,
            },
        }
        return json.dumps(log_data, ensure_ascii=False, indent=2)


def get_logger(name: str = "mcp_server") -> logging.Logger:
    """
    stdout으로 JSON 형식의 로그를 출력하는 로거를 반환합니다.

    Example:
        >>> from src.utils.logger import get_logger
        >>> logger = get_logger("my_module")
        >>> logger.info("Hello, World!")
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(JsonFormatter())

    logger.addHandler(handler)

    return logger
