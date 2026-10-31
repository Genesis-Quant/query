"""提供线程安全的令牌桶限流器。"""

import threading
import time


class RateLimiter:
    """按每秒请求数限流；0 表示不限制。"""

    def __init__(self, rate_per_second: int):
        """初始化令牌桶并校验非负速率。"""
        if rate_per_second < 0:
            raise ValueError("rate_per_second 不能小于 0")
        self.rate_per_second = rate_per_second
        self.capacity = float(rate_per_second)
        self.tokens = self.capacity
        self.last_time = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        """阻塞到获得一个令牌；不限流时立即返回。"""
        if self.rate_per_second == 0:
            return
        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last_time
                self.tokens = min(
                    self.capacity,
                    self.tokens + elapsed * self.rate_per_second,
                )
                self.last_time = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait_time = (1 - self.tokens) / self.rate_per_second
            time.sleep(wait_time)
