"""为惰性结果对象提供 DolphinDB 会话生命周期与按需下载。"""

from typing import Any, Self


class SessionResult:
    """持有一个会话，并执行任意 DolphinDB 脚本下载结果。"""

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
        """关闭结果持有的 DolphinDB 会话；重复调用是安全的。"""
        if self.closed:
            return
        self.session.close()
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
        """退出上下文时关闭 DolphinDB 会话。"""
        self.close()
        return False


__all__ = ["SessionResult"]
