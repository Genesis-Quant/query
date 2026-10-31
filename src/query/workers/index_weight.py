"""按自然日增量维护单个指数的成分股权重。"""

import pandas as pd

from query.config import DATA_START_DATE
from query.utils import (
    CODE_COLUMN,
    TIME_COLUMN,
    DateLike,
    index_weight_factor,
    normalize_date,
)
from query.utils.ts_api import get_pro

from .base import DateWorker


class IndexWeightWorker(DateWorker):
    """抓取一个指数并生成每日非零成分股权重。"""

    def __str__(self) -> str:
        """返回包含指数代码的权重 Worker 标识。"""
        return f"<IndexWeightWorker {self.index_code}>"

    def __init__(
            self,
            index_code: str,
            *,
            start_date: DateLike = DATA_START_DATE,
            end_date: DateLike | None = None,
            threads: int = 3,
            throttle: int = 8,
            max_retries: int = 3,
            retry_interval: float = 1.0,
            batch_size: int = 800_000,
            chunk_size: int = 50,
            overwrite: bool = False,
    ) -> None:
        """使用固定指数代码初始化逐自然日更新流程。"""
        self.index_code = str(index_code).strip().upper()
        super().__init__(
            start_date=start_date,
            end_date=end_date,
            threads=threads,
            throttle=throttle,
            max_retries=max_retries,
            retry_interval=retry_interval,
            batch_size=batch_size,
            chunk_size=chunk_size,
            overwrite=overwrite,
        )

    @property
    def factors(self) -> tuple[str, ...]:
        """返回当前指数对应的权重因子。"""
        return (index_weight_factor(self.index_code),)

    def fetch_one(self, current_date: pd.Timestamp) -> pd.DataFrame:
        """获取当前日期可用的最近指数快照并生成非零权重。"""
        current = normalize_date(current_date, "current_date")
        response = self.retry(
            lambda: get_pro().index_weight(
                index_code=self.index_code,
                end_date=current.strftime("%Y%m%d"),
            ),
            context=f"{self}[{current:%Y-%m-%d}]",
        )

        if response is None or response.empty:
            return self.EMPTY

        factor = self.factors[0]
        data = response[
            response["trade_date"].eq(response["trade_date"].max())
        ].rename(
            columns={"con_code": CODE_COLUMN, "weight": factor}
        )
        data[factor] = pd.to_numeric(data[factor], errors="coerce")
        data = data.loc[
            data[factor].notna() & data[factor].ne(0)
        ].copy()
        data[TIME_COLUMN] = current
        return self.melt(current, data)
