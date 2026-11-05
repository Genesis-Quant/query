"""按基金增量维护指定场内基金的日线数据。"""

from collections.abc import Callable, Sequence
from typing import Any

import pandas as pd

from query.utils import TIME_COLUMN
from query.utils.ts_api import get_pro

from .base import StockWorker

FUND_CODES = (
    # A 股宽基
    "510300.SH",
    "510500.SH",
    "512100.SH",
    "563300.SH",
    "510050.SH",
    "510180.SH",
    "510210.SH",
    "159901.SZ",
    "159949.SZ",
    "159915.SZ",
    "588000.SH",
    "588220.SH",
    # A 股行业
    "588200.SH",
    "515880.SH",
    "512170.SH",
    "159928.SZ",
    "515790.SH",
    "515220.SH",
    "512400.SH",
    "159870.SZ",
    "515210.SH",
    "512200.SH",
    "512800.SH",
    "512880.SH",
    "512660.SH",
    "159869.SZ",
    "159825.SZ",
    "159796.SZ",
    "159611.SZ",
    "159206.SZ",
    "562500.SH",
    "159852.SZ",
    "512980.SH",
    "159865.SZ",
    "516150.SH",
    "159766.SZ",
    "159326.SZ",
    "159851.SZ",
    # A 股策略
    "510880.SH",
    "512040.SH",
    "512890.SH",
    "159209.SZ",
    "159967.SZ",
    "159201.SZ",
    # 商品
    "518880.SH",
    "501018.SH",
    "159980.SZ",
    "159981.SZ",
    "159985.SZ",
    "161226.SZ",
    # 港股
    "513180.SH",
    "159920.SZ",
    "513120.SH",
    "513750.SH",
    "513070.SH",
    # 全球经济体
    "513400.SH",
    "513100.SH",
    "159941.SZ",
    "513500.SH",
    "159518.SZ",
    "159529.SZ",
    "159509.SZ",
    "513290.SH",
    "513080.SH",
    "513030.SH",
    "513880.SH",
    "513310.SH",
    "159687.SZ",
    "159329.SZ",
    "513730.SH",
    "160644.SZ",
    "520870.SH",
    "164824.SZ",
)
FUND_DAILY_FACTORS = ("open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount")
FUND_ADJ_FACTORS = ("adj_factor",)


def fetch_fund(
        worker: StockWorker,
        endpoint: Callable[..., pd.DataFrame],
        endpoint_name: str,
        code: str,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
) -> pd.DataFrame:
    """分页查询一只基金，并转换为统一长表。"""
    response = worker.paginator.fetch(
        endpoint,
        params={
            "ts_code": code,
            "start_date": start_date.strftime("%Y%m%d"),
            "end_date": end_date.strftime("%Y%m%d"),
            "fields": ",".join(("ts_code", "trade_date", *worker.factors)),
        },
        page_size=2_000,
        context=f"{worker}[{code}].{endpoint_name}",
        stop_on_short=True,
    )
    if response.empty:
        return worker.EMPTY
    return worker.melt(
        code,
        response.rename(columns={"trade_date": TIME_COLUMN}),
        start_date=start_date,
        end_date=end_date,
    )


class FundDailyWorker(StockWorker):
    """通过 fund_daily 接口更新指定场内基金的未复权日线。"""

    def __init__(
            self,
            codes: Sequence[str] = FUND_CODES,
            **kwargs: Any,
    ) -> None:
        """使用固定基金池或调用方指定的基金代码初始化。"""
        super().__init__(codes, **kwargs)

    def __str__(self) -> str:
        """返回基金日线 Worker 标识。"""
        return "<FundDailyWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        """返回 Tushare 场内基金日线字段。"""
        return FUND_DAILY_FACTORS

    def fetch_one(
            self,
            code: str,
            *,
            start_date: pd.Timestamp,
            end_date: pd.Timestamp,
    ) -> pd.DataFrame:
        """分页获取一只基金的日线并转换为统一长表。"""
        return fetch_fund(
            self,
            get_pro().fund_daily,
            "fund_daily",
            code,
            start_date,
            end_date,
        )


class FundAdjFactorWorker(StockWorker):
    """通过 fund_adj 接口更新指定场内基金的复权因子。"""

    def __init__(
            self,
            codes: Sequence[str] = FUND_CODES,
            **kwargs: Any,
    ) -> None:
        """使用固定基金池或调用方指定的基金代码初始化。"""
        super().__init__(codes, **kwargs)

    def __str__(self) -> str:
        """返回基金复权因子 Worker 标识。"""
        return "<FundAdjFactorWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        """返回 Tushare 基金复权因子字段。"""
        return FUND_ADJ_FACTORS

    def fetch_one(
            self,
            code: str,
            *,
            start_date: pd.Timestamp,
            end_date: pd.Timestamp,
    ) -> pd.DataFrame:
        """分页获取一只基金的复权因子并转换为统一长表。"""
        return fetch_fund(
            self,
            get_pro().fund_adj,
            "fund_adj",
            code,
            start_date,
            end_date,
        )
