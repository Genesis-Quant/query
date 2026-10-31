"""按自然日增量维护稀疏存储的 ST 股票特征。"""

import pandas as pd

from query.utils import (
    CODE_COLUMN,
    IS_ST_FACTOR,
    TIME_COLUMN,
    normalize_date,
)
from query.utils.ts_api import get_pro

from .base import DateWorker

STOCK_ST_FACTORS = (IS_ST_FACTOR,)


class StockSTWorker(DateWorker):
    """逐日抓取 ST 名单，只持久化 value=1 的股票。"""

    def __str__(self) -> str:
        """返回 ST 股票 Worker 标识。"""
        return "<StockSTWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        """返回 ST Worker 写入的因子。"""
        return STOCK_ST_FACTORS

    def fetch_one(self, current_date: pd.Timestamp) -> pd.DataFrame:
        """获取一个自然日的 ST 股票名单。"""
        current = normalize_date(current_date, "current_date")
        response = self.retry(
            lambda: get_pro().stock_st(
                trade_date=current.strftime("%Y%m%d"),
                fields="ts_code,trade_date",
            ),
            context=f"{self}[{current:%Y-%m-%d}]",
        )

        if response is None or response.empty:
            return self.EMPTY

        data = response.rename(
            columns={"trade_date": TIME_COLUMN, "ts_code": CODE_COLUMN}
        )
        data[self.factors[0]] = 1.0
        return self.melt(current, data)
