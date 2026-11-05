"""为惰性结果提供已有会话上的按需读取和结果生命周期。"""

from typing import Any, Self

from .logging import logger


class SessionResult:
    """借用已有会话执行读取，不管理会话生命周期。"""

    def __init__(
        self,
        *,
        session: Any,
    ) -> None:
        self.session = session
        self.closed = False

    def download(
        self,
        script: str,
    ) -> Any:
        """执行任意 DOS 代码并返回 session 的原始结果。"""
        if not isinstance(script, str) or not script.strip():
            raise ValueError("script 必须是非空 DOS 代码")
        if self.closed:
            raise RuntimeError("结果已关闭，无法继续从 session 下载")
        return self.session.run(script)

    def close(self) -> None:
        """标记结果关闭，不关闭调用方提供的会话。"""
        self.closed = True

    def __enter__(self) -> Self:
        """进入上下文并返回结果对象本身。"""
        if self.closed:
            raise RuntimeError("不能进入已经关闭的结果对象")
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: Any,
    ) -> bool:
        """退出时回收结果，清理失败不覆盖with块内的原始异常。"""
        try:
            self.close()
        except Exception as error:
            if exception_type is None:
                raise
            logger.warning(f"异常退出时关闭结果失败：{type(error).__name__}")
        return False


__all__ = ["SessionResult"]
