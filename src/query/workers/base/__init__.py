"""因子窄表 Worker 的公共基类。"""

from .date import DateWorker
from .stock import StockWorker
from .worker import BaseWorker

__all__ = ["BaseWorker", "DateWorker", "StockWorker"]
