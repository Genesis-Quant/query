"""导出写入 CoreData 的基础行情、行业和财务 Worker。"""

from query.config import INDEX_CODES
from query.utils import index_weight_factor

from .base import BaseWorker, DateWorker, StockWorker
from .fund_daily import FUND_ADJ_FACTORS, FUND_DAILY_FACTORS, FundAdjFactorWorker, FundDailyWorker
from .index_daily import INDEX_DAILY_FACTORS, IndexDailyWorker
from .index_weight import IndexWeightWorker
from .industry import INDUSTRY_FACTORS, IndustryWorker
from .stock_daily import (
    STOCK_ADJ_FACTOR_FACTORS,
    STOCK_DAILY_BASIC_FACTORS,
    STOCK_DAILY_FACTORS,
    STOCK_HFQ_FACTORS,
    STOCK_LIMIT_FACTORS,
    StockAdjFactorWorker,
    StockDailyBasicWorker,
    StockDailyWorker,
    StockHfqWorker,
    StockLimitWorker,
)
from .stock_financial import (
    FINANCIAL_FACTORS,
    StockBalanceSheetWorker,
    StockCashflowWorker,
    StockFinaIndicatorWorker,
    StockIncomeWorker,
)
from .stock_st import STOCK_ST_FACTORS, StockSTWorker

AVAILABLE_FACTORS = tuple(sorted({
    *FUND_ADJ_FACTORS,
    *FUND_DAILY_FACTORS,
    *INDUSTRY_FACTORS,
    *INDEX_DAILY_FACTORS,
    *STOCK_ADJ_FACTOR_FACTORS,
    *STOCK_DAILY_BASIC_FACTORS,
    *STOCK_DAILY_FACTORS,
    *STOCK_HFQ_FACTORS,
    *STOCK_LIMIT_FACTORS,
    *STOCK_ST_FACTORS,
    *FINANCIAL_FACTORS,
    *(index_weight_factor(index_code) for index_code in INDEX_CODES),
}))


def available_factors() -> tuple[str, ...]:
    """返回 CoreData 基础 Worker 声明的全部 factor。"""
    return AVAILABLE_FACTORS


__all__ = [
    "BaseWorker", "DateWorker", "StockWorker", "FundAdjFactorWorker", "FundDailyWorker",
    "IndustryWorker", "IndexDailyWorker", "IndexWeightWorker", "StockAdjFactorWorker",
    "StockBalanceSheetWorker", "StockCashflowWorker", "StockDailyBasicWorker",
    "StockDailyWorker", "StockFinaIndicatorWorker", "StockHfqWorker", "StockIncomeWorker",
    "StockLimitWorker", "StockSTWorker", "available_factors",
]
