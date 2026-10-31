"""定义股票行情相关接口各自独立的数据更新 Worker。"""

import pandas as pd

from query.utils import CODE_COLUMN, TIME_COLUMN, get_codes, normalize_date
from query.utils.ts_api import get_pro, ts

from .base import DateWorker, StockWorker

STOCK_DAILY_FACTORS = ("open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount")
STOCK_LIMIT_FACTORS = ("up_limit", "down_limit")
STOCK_DAILY_BASIC_FACTORS = (
    "turnover_rate", "turnover_rate_f", "volume_ratio", "limit_status", "pe", "pe_ttm", "pb", "ps", "ps_ttm",
    "dv_ratio", "dv_ttm", "total_share", "float_share", "free_share", "total_mv", "circ_mv",
)
STOCK_ADJ_FACTOR_FACTORS = ("adj_factor",)
STOCK_HFQ_FACTORS = ("open_hfq", "high_hfq", "low_hfq", "close_hfq", "change_hfq", "pct_chg_hfq")


def fetch_daily(
        worker: DateWorker,
        endpoint: str,
        current_date: pd.Timestamp,
) -> pd.DataFrame:
    """调用按交易日查询的行情接口，并转换为统一长表。"""
    current = normalize_date(current_date, "current_date")
    response = worker.retry(
        lambda: getattr(get_pro(), endpoint)(
            trade_date=current.strftime("%Y%m%d"),
            fields=",".join(("ts_code", "trade_date", *worker.factors)),
        ),
        context=f"{worker}[{current:%Y-%m-%d}]",
    )
    if response is None or response.empty:
        return worker.EMPTY
    return worker.melt(current, response.rename(columns={
        "trade_date": TIME_COLUMN,
        "ts_code": CODE_COLUMN,
    }))


class StockDailyWorker(DateWorker):
    """通过 daily 接口按自然日更新全市场未复权行情。"""

    def __str__(self) -> str:
        """返回未复权日行情 Worker 标识。"""
        return "<StockDailyWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        return STOCK_DAILY_FACTORS

    @property
    def incremental_scope_codes(self) -> tuple[str, ...]:
        """只使用股票代码计算增量基线，排除基金日线。"""
        return get_codes()

    def fetch_one(self, current_date: pd.Timestamp) -> pd.DataFrame:
        """获取一个自然日的全市场未复权日行情。"""
        return fetch_daily(self, "daily", current_date)


class StockLimitWorker(DateWorker):
    """通过 stk_limit 接口按自然日更新全市场涨跌停价格。"""

    def __str__(self) -> str:
        """返回涨跌停价格 Worker 标识。"""
        return "<StockLimitWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        return STOCK_LIMIT_FACTORS

    def fetch_one(self, current_date: pd.Timestamp) -> pd.DataFrame:
        """获取一个自然日的全市场涨跌停价格。"""
        return fetch_daily(self, "stk_limit", current_date)


class StockDailyBasicWorker(DateWorker):
    """通过 daily_basic 接口按自然日更新全市场估值和市值指标。"""

    def __str__(self) -> str:
        """返回每日指标 Worker 标识。"""
        return "<StockDailyBasicWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        return STOCK_DAILY_BASIC_FACTORS

    def fetch_one(self, current_date: pd.Timestamp) -> pd.DataFrame:
        """获取一个自然日的全市场估值和市值指标。"""
        return fetch_daily(self, "daily_basic", current_date)


class StockAdjFactorWorker(DateWorker):
    """通过 adj_factor 接口按自然日更新全市场复权因子。"""

    def __str__(self) -> str:
        """返回复权因子 Worker 标识。"""
        return "<StockAdjFactorWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        return STOCK_ADJ_FACTOR_FACTORS

    @property
    def incremental_scope_codes(self) -> tuple[str, ...]:
        """只使用股票代码计算增量基线，排除基金复权因子。"""
        return get_codes()

    def fetch_one(self, current_date: pd.Timestamp) -> pd.DataFrame:
        """获取一个自然日的全市场复权因子。"""
        return fetch_daily(self, "adj_factor", current_date)


class StockHfqWorker(StockWorker):
    """通过 pro_bar 接口更新后复权日行情。"""

    def __str__(self) -> str:
        """返回后复权日行情 Worker 标识。"""
        return "<StockHfqWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        return STOCK_HFQ_FACTORS

    def fetch_one(
            self,
            code: str,
            *,
            start_date: pd.Timestamp,
            end_date: pd.Timestamp,
    ) -> pd.DataFrame:
        """获取一只股票的后复权日行情。"""

        def fetch_bar() -> pd.DataFrame | None:
            try:
                return ts.pro_bar(
                    ts_code=code,
                    adj="hfq",
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                )
            except OSError as error:
                # Tushare pro_bar 会吞掉内部异常，并在重试耗尽后统一抛出
                # IOError("ERROR.")；按约定将这个哨兵异常视为本次无数据。
                if error.args == ("ERROR.",):
                    return None
                raise

        response = self.retry(
            fetch_bar,
            context=f"{self}[{code}]",
        )

        if response is None or response.empty:
            return self.EMPTY

        return self.melt(code, response.rename(
            columns={
                "trade_date": TIME_COLUMN,
                "open": "open_hfq",
                "high": "high_hfq",
                "low": "low_hfq",
                "close": "close_hfq",
                "change": "change_hfq",
                "pct_chg": "pct_chg_hfq",
            }
        ), start_date=start_date, end_date=end_date)
