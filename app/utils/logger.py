"""
日志工具 - 基于 loguru 的结构化 JSON 日志

日志格式至少包含：时间、级别、模块、请求 ID、用户 ID 或匿名会话 ID、事件内容。
不记录密码、验证码、Token、身份证号、完整手机号、支付信息和第三方密钥。

参考：.agent/conventions.md §7
"""

import json
import sys

from loguru import logger

from app.config import settings


def json_formatter(record: dict) -> str:
    """
    结构化 JSON 日志格式。

    输出示例：
        {"time":"2026-07-06T10:30:00+08:00","level":"INFO","module":"app.agents",
         "request_id":"req_xxx","user_id":"u_xxx","message":"景点规划完成"}
    """
    log_entry = {
        "time": record["time"].strftime("%Y-%m-%dT%H:%M:%S%z"),
        "level": record["level"].name,
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
    }

    # 合并额外绑定的上下文字段（request_id、user_id 等）
    extra = record.get("extra", {})
    log_entry.update(extra)

    # 序列化异常信息
    if record.get("exception"):
        log_entry["exception"] = str(record["exception"])

    return json.dumps(log_entry, ensure_ascii=False, default=str) + "\n"


# 移除默认 handler
logger.remove()

# 控制台输出（结构化 JSON）
logger.add(
    sys.stdout,
    format=json_formatter,
    level=settings.LOG_LEVEL,
    colorize=False,  # JSON 不需要着色
)

# 文件输出（结构化 JSON，按天轮转）
logger.add(
    "logs/app_{time:YYYY-MM-DD}.jsonl",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    format=json_formatter,
    level="INFO",
)

__all__ = ["logger"]
