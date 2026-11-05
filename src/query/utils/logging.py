"""复用调用方的 Loguru 配置，不移除 sink、不更改日志格式。"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

if "loguru" not in sys.modules and "LOGURU_AUTOINIT" not in os.environ:
    # 仅接管尚未初始化的默认输出；不删除调用方的任何sink，也不更改日志格式。
    os.environ["LOGURU_AUTOINIT"] = "False"
    from loguru import logger

    del os.environ["LOGURU_AUTOINIT"]
    logger.add(sys.stdout, diagnose=False)
else:
    from loguru import logger

__all__ = ["logger", "add_worker_file_log"]


def error_text(error: BaseException) -> str:
    """保留脱敏的异常类型和原因，不携带第三方调用栈或认证响应。"""
    text = f"{type(error).__name__}: {error}"
    secrets = {
        value for name, value in os.environ.items()
        if value and any(marker in name.upper() for marker in ("TOKEN", "PASSWORD", "SECRET", "API_KEY"))
    }
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(https?://)[^/\s@]+@", r"\1[REDACTED]@", text)
    return re.sub(
        r'''(?i)((?:token|password|secret|api[_-]?key)["']?\s*[:=]\s*)(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s,;&}\]]+)''',
        r"\1[REDACTED]", text,
    )


def add_worker_file_log(path: Path | None = None) -> Path:
    """为显式 CLI 运行追加持久日志，不移除现有 sink、不修改日志格式。"""
    if path is None:
        name = f"{datetime.now():%Y%m%d-%H%M%S}-{os.getpid()}-{uuid4().hex[:8]}.log"
        path = Path.cwd() / "output" / "workers" / name
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("x", encoding="utf-8")
    secrets = sorted({
        value for name, value in os.environ.items()
        if value and any(marker in name.upper() for marker in ("TOKEN", "PASSWORD", "SECRET", "API_KEY"))
    }, key=len, reverse=True)

    def write(message: str) -> None:
        text = str(message)
        for secret in secrets:
            text = text.replace(secret, "[REDACTED]")
        stream.write(text)
        stream.flush()

    # 不序列化调用栈局部变量，避免第三方客户端凭据进入持久日志。
    logger.add(write, level="DEBUG", backtrace=False, diagnose=False, catch=False)
    return path
