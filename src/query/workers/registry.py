"""增量数据 Worker 的规范名称、说明和名称校验。"""

from collections.abc import Sequence

WORKER_ORDER = (
    "daily",
    "fund-daily",
    "fund-adj-factor",
    "limit",
    "daily-basic",
    "adj-factor",
    "hfq",
    "st",
    "industry",
    "balance-sheet",
    "income",
    "cashflow",
    "fina-indicator",
    "index-daily",
    "index-weight",
)

WORKER_DESCRIPTIONS = {
    "daily": "全市场未复权日行情",
    "index-daily": "配置指数未复权日行情",
    "fund-daily": "指定场内基金池未复权日线",
    "fund-adj-factor": "指定场内基金池复权因子",
    "limit": "全市场每日涨跌停价格",
    "daily-basic": "全市场每日估值和市值指标",
    "adj-factor": "全市场复权因子",
    "hfq": "逐股票后复权日行情",
    "st": "全市场 ST 名单",
    "industry": "全市场动态申万行业分类",
    "balance-sheet": "逐股票资产负债表",
    "income": "逐股票利润表及 TTM 因子",
    "cashflow": "逐股票现金流量表及 TTM 因子",
    "fina-indicator": "逐股票财务指标",
    "index-weight": "指数成分股权重；每个指数创建一个 Worker",
}

WORKER_ALIASES = {
    "stock-daily": "daily",
    "stockdailyworker": "daily",
    "index": "index-daily",
    "indexdaily": "index-daily",
    "indexdailyworker": "index-daily",
    "fund": "fund-daily",
    "funddailyworker": "fund-daily",
    "fund-adj": "fund-adj-factor",
    "fundadjfactorworker": "fund-adj-factor",
    "stock-limit": "limit",
    "stocklimitworker": "limit",
    "stock-daily-basic": "daily-basic",
    "stockdailybasicworker": "daily-basic",
    "stock-adj-factor": "adj-factor",
    "stockadjfactorworker": "adj-factor",
    "stock-hfq": "hfq",
    "stockhfqworker": "hfq",
    "stock-st": "st",
    "stockstworker": "st",
    "industry-worker": "industry",
    "industryworker": "industry",
    "balancesheet": "balance-sheet",
    "stock-balance-sheet": "balance-sheet",
    "stockbalancesheetworker": "balance-sheet",
    "stock-income": "income",
    "stockincomeworker": "income",
    "stock-cashflow": "cashflow",
    "stockcashflowworker": "cashflow",
    "stock-fina-indicator": "fina-indicator",
    "stockfinaindicatorworker": "fina-indicator",
    "indexweight": "index-weight",
    "indexweightworker": "index-weight",
}

DATE_WORKERS = frozenset({
    "daily",
    "limit",
    "daily-basic",
    "adj-factor",
    "st",
    "index-weight",
})

STOCK_WORKERS = frozenset({
    "fund-adj-factor",
    "fund-daily",
    "hfq",
    "balance-sheet",
    "income",
    "cashflow",
    "fina-indicator",
})


def normalize_worker_names(values: Sequence[str]) -> tuple[str, ...]:
    """规范 Worker 名称、展开 all，并保持用户给定的执行顺序。"""
    if not values:
        raise ValueError("至少指定一个 Worker，或使用 all")

    normalized: list[str] = []
    for value in values:
        key = value.strip().lower().replace("_", "-")
        key = WORKER_ALIASES.get(key, key)
        if key == "all":
            if len(values) != 1:
                raise ValueError("all 不能与其他 Worker 同时使用")
            return WORKER_ORDER
        if key not in WORKER_DESCRIPTIONS:
            available = "、".join(WORKER_ORDER)
            raise ValueError(
                f"未知 Worker：{value!r}；可用值：{available}、all"
            )
        if key not in normalized:
            normalized.append(key)
    return tuple(normalized)


__all__ = [
    "DATE_WORKERS",
    "STOCK_WORKERS",
    "WORKER_ALIASES",
    "WORKER_DESCRIPTIONS",
    "WORKER_ORDER",
    "normalize_worker_names",
]
