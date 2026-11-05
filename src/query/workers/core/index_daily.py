"""按指数代码增量维护配置指数的未复权日行情。"""

from collections.abc import Sequence
from typing import Any

import pandas as pd

from query.config import INDEX_CODES
from query.utils import TIME_COLUMN
from query.utils.ts_api import get_pro

from .base import StockWorker
from .stock_daily import STOCK_DAILY_FACTORS

INDEX_DAILY_FACTORS = STOCK_DAILY_FACTORS


class IndexDailyWorker(StockWorker):
    """通过 index_daily 接口更新配置指数的未复权日行情。"""

    def __init__(
            self,
            codes: Sequence[str] = INDEX_CODES,
            **kwargs: Any,
    ) -> None:
        """使用配置指数池或调用方指定的指数代码初始化。"""
        super().__init__(codes, **kwargs)

    def __str__(self) -> str:
        """返回指数日行情 Worker 标识。"""
        return "<IndexDailyWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        """返回 Tushare 指数日行情字段。"""
        return INDEX_DAILY_FACTORS

    def fetch_one(
            self,
            code: str,
            *,
            start_date: pd.Timestamp,
            end_date: pd.Timestamp,
    ) -> pd.DataFrame:
        """分页获取一个指数的日行情并转换为统一长表。"""
        response = self.paginator.fetch(
            get_pro().index_daily,
            params={
                "ts_code": code,
                "start_date": start_date.strftime("%Y%m%d"),
                "end_date": end_date.strftime("%Y%m%d"),
                "fields": ",".join(
                    ("ts_code", "trade_date", *self.factors)
                ),
            },
            page_size=5_000,
            context=f"{self}[{code}].index_daily",
            stop_on_short=True,
        )
        if response.empty:
            return self.EMPTY
        return self.melt(
            code,
            response.rename(columns={"trade_date": TIME_COLUMN}),
            start_date=start_date,
            end_date=end_date,
        )
