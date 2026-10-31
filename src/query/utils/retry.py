"""提供可复用的限流重试执行器。"""

import time
from collections.abc import Callable

from .logging import logger
from .throttle import RateLimiter


class Retry:
    """使用初始化时的统一配置执行受限操作并重试异常。"""

    def __init__(
            self,
            max_retries: int,
            retry_interval: float,
            limiter: RateLimiter,
    ) -> None:
        """保存重试次数、重试间隔和限流器。"""
        if max_retries <= 0:
            raise ValueError("max_retries 必须大于 0")
        if retry_interval < 0:
            raise ValueError("retry_interval 不能小于 0")

        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.limiter = limiter

    def __call__[Result](
            self,
            operation: Callable[[], Result],
            *,
            context: str,
    ) -> Result:
        """执行操作，失败时重新限流并重试。"""
        if not context:
            raise ValueError("context 不能为空")

        attempt = 0
        while True:
            attempt += 1
            try:
                self.limiter.acquire()
                result = operation()
                if attempt > 1:
                    logger.info(
                        f"{context} 请求恢复："
                        f"第 {attempt}/{self.max_retries} 次尝试成功"
                    )
                return result
            except Exception as error:
                if attempt >= self.max_retries:
                    raise RuntimeError(
                        f"{context} 获取失败，"
                        f"共尝试 {self.max_retries} 次：{error}"
                    ) from error
                logger.exception(
                    f"{context} 请求重试："
                    f"attempt={attempt}/{self.max_retries}，"
                    f"retry_in={self.retry_interval:g}秒"
                )
                time.sleep(self.retry_interval)
