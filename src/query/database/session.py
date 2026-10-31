"""创建并预加载当前 Python 包编译结果的独立 DolphinDB 会话。"""

import json
from hashlib import sha256
from threading import Lock, Timer
from time import monotonic
from typing import Any, Literal

import dolphindb

from query.settings import DolphinSettings
from query.utils import logger, validate_dolphindb_identifier

from .compile.query.scripts import build_script

COMPILED_QUERY = build_script()


class LoguruSink(dolphindb.logger.Sink):
    def __init__(self) -> None:
        super().__init__("loguru")

    def handle(self, message: Any) -> None:
        logger.log(message.level.name, message.log.rstrip("\r\n"))

    def flush(self) -> None:
        return None


def redirect_session_output(session: Any) -> None:
    message_logger = session.msg_logger
    message_logger.disable_stdout_sink()
    if not any(sink.name == "loguru" for sink in message_logger.list_sinks()):
        message_logger.add_sink(LoguruSink())


def initialize_session(session: Any) -> None:
    """每个连接首次使用时执行本地编译的 DOS，不依赖服务端 query 模块。"""
    marker = "queryCompilation"
    fingerprint = sha256(COMPILED_QUERY.encode("utf-8")).hexdigest()
    exists = session.run(f"{json.dumps(marker)} in objs(true).name")
    if bool(exists) and session.run(marker) == fingerprint:
        return
    session.run(COMPILED_QUERY)
    session.upload({marker: fingerprint})


def has_session_variable(session: Any, name: str, *, log_progress: bool = True) -> bool:
    validate_dolphindb_identifier(name)
    return bool(session.run(f"`{name} in objs(true).name"))


class DeadlineSession:
    """可选的会话总寿命限制，不重连、不重放脚本。"""

    def __init__(self, session: Any, max_time: int) -> None:
        self.raw_session = session
        self.max_time = max_time
        self.deadline = monotonic() + max_time
        self.lock = Lock()
        self.closed = False
        self.expired = False
        self.timer = Timer(max_time, self.expire)
        self.timer.daemon = True
        self.timer.start()

    def ensure_open(self) -> None:
        if self.expired or monotonic() >= self.deadline:
            self.expire()
            raise TimeoutError(f"DolphinDB Session 已超过最长使用时间 {self.max_time} 秒")
        if self.closed:
            raise RuntimeError("DolphinDB Session 已关闭")

    def run(self, script: str, *args: Any, **kwargs: Any) -> Any:
        self.ensure_open()
        try:
            result = self.raw_session.run(script, *args, **kwargs)
        except Exception as error:
            if self.expired:
                raise TimeoutError("DolphinDB Session 已超过最长使用时间") from error
            raise
        self.ensure_open()
        return result

    def upload(self, variables: dict[str, Any]) -> Any:
        self.ensure_open()
        result = self.raw_session.upload(variables)
        self.ensure_open()
        return result

    def expire(self) -> None:
        with self.lock:
            if self.closed:
                return
            self.expired = True
            self.closed = True
        try:
            self.raw_session.close()
        except Exception as error:
            logger.warning(f"DolphinDB Session 超时关闭失败：{type(error).__name__}")

    def close(self) -> None:
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.timer.cancel()
        self.raw_session.close()

    def __getattr__(self, name: str) -> Any:
        self.ensure_open()
        return getattr(self.raw_session, name)


def create_session(
    settings: DolphinSettings | None = None,
    *,
    role: Literal["runtime", "worker"] = "runtime",
    redirect_output: bool = True,
    max_time: int | None = None,
) -> Any:
    """连接后立即加载 DOS；初始化失败关闭该连接并报错，不重放任务。"""
    if max_time is not None and (isinstance(max_time, bool) or not isinstance(max_time, int) or max_time <= 0):
        raise ValueError("max_time 必须是正整数秒数或 None")
    selected = settings if settings is not None else DolphinSettings.from_env(role=role)
    failures = []
    for endpoint in selected.endpoints:
        host, port = endpoint.rsplit(":", 1)
        session = dolphindb.session()
        try:
            if redirect_output:
                redirect_session_output(session)
            connected = session.connect(host.strip("[]"), int(port), selected.username,
                                        selected.password.get_secret_value(),
                                        highAvailability=False, reconnect=False)
            if not connected:
                raise ConnectionError("服务端未接受连接")
        except Exception as error:
            message = str(error).replace(selected.password.get_secret_value(), "[REDACTED]")
            failures.append(f"{endpoint}：{message}")
            try:
                session.close()
            except Exception:
                pass
            continue
        current = session if max_time is None else DeadlineSession(session, max_time)
        try:
            initialize_session(current)
        except BaseException:
            try:
                current.close()
            except Exception as error:
                logger.warning(f"初始化失败后关闭会话异常：{type(error).__name__}")
            raise
        return current
    raise ConnectionError(f"所有 DolphinDB 端点均连接失败：{'；'.join(failures)}") from None
