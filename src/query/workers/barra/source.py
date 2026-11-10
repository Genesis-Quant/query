"""用 Query DSL 替代 Cal.dos；所有财报、行情和三级因子均来自指定窄表。"""

from datetime import date, timedelta

import pandas as pd

from query.config import DATA_START_DATE, BarraConfig
from query.execute.schema import FactorQuery

DESCRIPTORS = tuple(
    factor for factors in BarraConfig.second_factors.values() for factor in factors
)


def window_weights(window: int, half_life: int) -> list[float]:
    """沿用官方 Cal 的 ewmMean(0..window-1) 归一化位置权重，不改成无限 EWM。"""
    values = pd.Series(range(window), dtype=float).ewm(halflife=half_life, adjust=True).mean()
    return (values / values.sum()).tolist()


def industry_query(
    start: date, end: date, codes: list[str], *, config: type[BarraConfig] = BarraConfig,
) -> FactorQuery:
    """行业是事件序列，显式读取起始日以来事件；不修改通用 Query 的 seed 规则。"""
    history = date.fromisoformat(DATA_START_DATE)
    return FactorQuery(
        start_date=start.isoformat(), end_date=end.isoformat(), codes=codes,
        lookback=timedelta(days=max(0, (start - history).days)),
        factors=[f"industry_l{config.industry_level}"],
    )


def dataset_query(
    start: date, end: date, codes: list[str], *, config: type[BarraConfig] = BarraConfig,
    cross_section: bool = True,
) -> FactorQuery:
    """日频迁移的36个描述子；可延后Midcap截面计算，其余计算不变。"""
    benchmark = config.benchmark
    derivatives = {
        # 市值单位从万元转元；仅用同日股价×同日万股股数补缺，不前填行情。
        "reported_market_cap": {
            "type": "DIRECT", "op": "binary.mul",
            "fields": {"left": "total_mv", "right": 10000.0},
        },
        "reported_float_cap": {
            "type": "DIRECT", "op": "binary.mul",
            "fields": {"left": "circ_mv", "right": 10000.0},
        },
        "market_cap": {
            "type": "DIRECT", "op": "multiary.coalesce", "fields": {"cols": [
                "reported_market_cap",
                {"type": "DIRECT", "op": "binary.mul", "fields": {
                    "left": {"type": "DIRECT", "op": "binary.mul", "fields": {"left": "close", "right": "total_share"}},
                    "right": 10000.0,
                }},
            ]},
        },
        "float_cap": {
            "type": "DIRECT", "op": "multiary.coalesce", "fields": {"cols": [
                "reported_float_cap",
                {"type": "DIRECT", "op": "binary.mul", "fields": {
                    "left": {"type": "DIRECT", "op": "binary.mul", "fields": {"left": "close", "right": "float_share"}},
                    "right": 10000.0,
                }},
            ]},
        },
        "market_cap_proxy": {
            "type": "DIRECT", "op": "multiary.and", "fields": {"cols": [
                {"type": "DIRECT", "op": "unary.is_null", "fields": {"col": "reported_market_cap"}},
                {"type": "DIRECT", "op": "unary.is_finite", "fields": {"col": "market_cap"}},
                {"type": "DIRECT", "op": "binary.gt", "fields": {"left": "market_cap", "right": 0.0}},
            ]},
        },
        "float_cap_proxy": {
            "type": "DIRECT", "op": "multiary.and", "fields": {"cols": [
                {"type": "DIRECT", "op": "unary.is_null", "fields": {"col": "reported_float_cap"}},
                {"type": "DIRECT", "op": "unary.is_finite", "fields": {"col": "float_cap"}},
                {"type": "DIRECT", "op": "binary.gt", "fields": {"left": "float_cap", "right": 0.0}},
            ]},
        },
        "market_valid": {
            "type": "DIRECT", "op": "multiary.and",
            "fields": {"cols": [
                {"type": "DIRECT", "op": "unary.is_finite", "fields": {"col": "close"}},
                {"type": "DIRECT", "op": "unary.is_finite", "fields": {"col": "market_cap"}},
                {"type": "DIRECT", "op": "unary.is_finite", "fields": {"col": "float_cap"}},
                {"type": "DIRECT", "op": "binary.gt", "fields": {"left": "close", "right": 0.0}},
                {"type": "DIRECT", "op": "binary.gt", "fields": {"left": "market_cap", "right": 0.0}},
                {"type": "DIRECT", "op": "binary.gt", "fields": {"left": "float_cap", "right": 0.0}},
            ]},
        },
        "return_day": {
            "type": "DIRECT", "op": "binary.div",
            "fields": {"left": "pct_chg", "right": 100.0},
        },
        "benchmark_return": {
            "type": "DIRECT", "op": "binary.div",
            "fields": {"left": f"pct_chg@{benchmark}", "right": 100.0},
        },
        "excess_return": {
            "type": "DIRECT", "op": "binary.sub",
            "fields": {"left": "return_day", "right": "benchmark_return"},
        },
        "log_relative_return": {
            "type": "DIRECT", "op": "binary.sub",
            "fields": {
                "left": {"type": "DIRECT", "op": "unary.log1p", "fields": {"col": "return_day"}},
                "right": {"type": "DIRECT", "op": "unary.log1p", "fields": {"col": "benchmark_return"}},
            },
        },
        "return_observed": {
            "type": "DIRECT", "op": "multiary.and",
            "fields": {"cols": [
                {"type": "DIRECT", "op": "unary.is_finite", "fields": {"col": "return_day"}},
                {"type": "DIRECT", "op": "unary.is_finite", "fields": {"col": "benchmark_return"}},
                {"type": "DIRECT", "op": "binary.gt", "fields": {"left": "return_day", "right": -1.0}},
                {"type": "DIRECT", "op": "binary.gt", "fields": {"left": "benchmark_return", "right": -1.0}},
            ]},
        },
        "return_valid": {
            "type": "DIRECT", "op": "multiary.and",
            "fields": {"cols": [
                "return_observed",
                {"type": "DIRECT", "op": "binary.gt", "fields": {"left": "vol", "right": 0.0}},
            ]},
        },
        "history_observations": {
            "type": "TS", "op": "unary.cum_count", "fields": {"col": "close"},
        },
        "eligible": {
            "type": "DIRECT", "op": "multiary.and",
            "fields": {"cols": [
                "market_valid",
                {"type": "DIRECT", "op": "binary.eq", "fields": {"left": "is_st", "right": 0.0}},
                {"type": "DIRECT", "op": "binary.ge", "fields": {"left": "history_observations", "right": config.min_listing_days}},
            ]},
        },
        "month_key": {
            "type": "DIRECT", "op": "binary.add",
            "fields": {
                "left": {"type": "DIRECT", "op": "binary.mul", "fields": {
                    "left": {"type": "DIRECT", "op": "unary.year", "fields": {"col": "time"}}, "right": 12,
                }},
                "right": {"type": "DIRECT", "op": "unary.month", "fields": {"col": "time"}},
            },
        },
        "monthly_sample": {
            "type": "DIRECT", "op": "binary.ne",
            "fields": {"left": "month_key", "right": {
                "type": "TS", "op": "unary.shift", "fields": {"col": "month_key"}, "params": {"periods": 1},
            }},
        },
        "sample_month": {
            "type": "TS", "op": "unary.shift",
            "fields": {"col": {"type": "DIRECT", "op": "unary.month", "fields": {"col": "time"}}},
            "params": {"periods": 1},
        },
        "sample_year": {
            "type": "TS", "op": "unary.shift",
            "fields": {"col": {"type": "DIRECT", "op": "unary.year", "fields": {"col": "time"}}},
            "params": {"periods": 1},
        },
        # 相同口径优先；金融企业未披露流动/非流动分类时，已披露债券是较窄的杠杆代理。
        "long_liability": {
            "type": "DIRECT", "op": "multiary.coalesce", "fields": {"cols": [
                "total_ncl",
                {"type": "DIRECT", "op": "binary.sub", "fields": {"left": "total_liab", "right": "total_cur_liab"}},
                "bond_payable",
            ]},
        },
        "long_liability_proxy": {
            "type": "DIRECT", "op": "multiary.and", "fields": {"cols": [
                {"type": "DIRECT", "op": "unary.is_null", "fields": {"col": "total_ncl"}},
                {"type": "DIRECT", "op": "unary.is_null", "fields": {"col": {
                    "type": "DIRECT", "op": "binary.sub", "fields": {"left": "total_liab", "right": "total_cur_liab"},
                }}},
                {"type": "DIRECT", "op": "unary.not_null", "fields": {"col": "bond_payable"}},
            ]},
        },
        "cash_equivalents": {
            "type": "DIRECT", "op": "multiary.coalesce",
            "fields": {"cols": ["c_cash_equ_end_period", "money_cap"]},
        },
        "operating_cost": {
            "type": "DIRECT", "op": "multiary.coalesce",
            "fields": {"cols": ["oper_cost_ttm", "total_cogs_ttm"]},
        },
        "cost_proxy": {
            "type": "DIRECT", "op": "binary.and", "fields": {
                "left": {"type": "DIRECT", "op": "unary.is_null", "fields": {"col": "oper_cost_ttm"}},
                "right": {"type": "DIRECT", "op": "unary.not_null", "fields": {"col": "operating_cost"}},
            },
        },
        "gross_profit": {
            "type": "DIRECT", "op": "binary.sub",
            "fields": {"left": "revenue_ttm", "right": "operating_cost"},
        },
        # 缺TTM EBIT时优先利润总额+利息支出，最后使用已披露年报EBIT，显式保留代理标记。
        "earnings_before_interest": {
            "type": "DIRECT", "op": "multiary.coalesce", "fields": {"cols": [
                "ebit_ttm",
                {"type": "DIRECT", "op": "binary.add", "fields": {"left": "total_profit_ttm", "right": "fin_exp_int_exp_ttm"}},
                "ebit_4",
            ]},
        },
        "ebit_proxy": {"type": "DIRECT", "op": "binary.and", "fields": {
            "left": {"type": "DIRECT", "op": "unary.is_null", "fields": {"col": "ebit_ttm"}},
            "right": {"type": "DIRECT", "op": "unary.not_null", "fields": {"col": "earnings_before_interest"}},
        }},
        "dividend_yield": {
            "type": "DIRECT", "op": "multiary.coalesce", "fields": {"cols": ["dv_ttm", "dv_ratio"]},
        },
        "dividend_proxy": {
            "type": "DIRECT", "op": "binary.and", "fields": {
                "left": {"type": "DIRECT", "op": "unary.is_null", "fields": {"col": "dv_ttm"}},
                "right": {"type": "DIRECT", "op": "unary.not_null", "fields": {"col": "dividend_yield"}},
            },
        },
        "balance_accrual_ratio": {
            "type": "DIRECT", "op": "binary.div", "fields": {
                "left": {"type": "DIRECT", "op": "binary.sub", "fields": {
                    "left": {"type": "DIRECT", "op": "binary.sub", "fields": {"left": "total_assets", "right": "cash_equivalents"}},
                    # total_ncl+total_cur_liab=total_liab；使用总负债避免金融企业分类缺失。
                    "right": "total_liab",
                }},
                "right": "total_assets",
            },
        },
        "abs": {
            "type": "TS", "op": "unary.ffill", "fields": {"col": {
                "type": "DIRECT", "op": "unary.neg", "fields": {"col": {
                    "type": "TS", "op": "unary.diff", "fields": {"col": {
                        "type": "TS", "op": "unary.shift", "fields": {"col": "balance_accrual_ratio"}, "params": {"periods": 1},
                    }}, "params": {"periods": 1}, "on": "monthly_sample",
                }},
            }},
        },
        "acf_ttm": {
            "type": "DIRECT", "op": "unary.neg", "fields": {"col": {
                "type": "DIRECT", "op": "binary.div", "fields": {
                    "left": {"type": "DIRECT", "op": "binary.sub", "fields": {
                        "left": {"type": "DIRECT", "op": "binary.sub", "fields": {"left": "n_income_attr_p_ttm", "right": "n_cashflow_act_ttm"}},
                        "right": "n_incr_cash_cash_equ_ttm",
                    }}, "right": "total_assets",
                },
            }},
        },
        "annual_share_sum": {
            "type": "TS", "op": "unary.rolling_sum", "fields": {"col": {
                "type": "DIRECT", "op": "binary.mul", "fields": {"left": "total_share", "right": 10000.0},
            }}, "params": {"window": "1y", "min_periods": 1},
        },
        "earnings_per_share": {
            "type": "DIRECT", "op": "binary.div", "fields": {"left": "n_income_attr_p_ttm", "right": "annual_share_sum"},
        },
        "sales_per_share": {
            "type": "DIRECT", "op": "binary.div", "fields": {"left": "revenue_ttm", "right": "annual_share_sum"},
        },
        # 官方CXGRO明确使用处置长期资产现金；不偷换为购建资本开支。
        "capital_disposal": {
            "type": "DIRECT", "op": "multiary.coalesce", "fields": {"cols": ["n_recp_disp_fiolta_ttm", "n_recp_disp_fiolta_4"]},
        },
        "capital_disposal_proxy": {
            "type": "DIRECT", "op": "binary.and", "fields": {
                "left": {"type": "DIRECT", "op": "unary.is_null", "fields": {"col": "n_recp_disp_fiolta_ttm"}},
                "right": {"type": "DIRECT", "op": "unary.not_null", "fields": {"col": "capital_disposal"}},
            },
        },
        "float_month_sum": {
            "type": "TS", "op": "unary.cum_sum", "fields": {"col": {
                "type": "DIRECT", "op": "binary.div", "fields": {"left": "float_cap", "right": 10000.0},
            }}, "by": "month_key",
        },
        "lncap": {
            "type": "DIRECT", "op": "unary.log", "fields": {"col": {
                "type": "DIRECT", "op": "binary.mul", "fields": {"left": "float_month_sum", "right": 10000.0},
            }},
        },
        # 同一截面共同缩放不改变三次项残差的最终zscore，避免市值立方造成数值秩丢失。
        "scaled_float_month_sum": {
            "type": "DIRECT", "op": "binary.div", "fields": {
                "left": "float_month_sum", "right": {"type": "CS", "op": "unary.mean", "fields": {"col": "float_month_sum"}, "on": "market_valid"},
            },
        },
        "midcap_residual": {
            "type": "CS", "op": "binary.residual", "fields": {
                "left": "scaled_float_month_sum",
                "right": {"type": "DIRECT", "op": "binary.pow", "fields": {"left": "scaled_float_month_sum", "right": 3.0}},
            }, "on": "market_valid",
        },
        "midcap": {
            "type": "CS", "op": "unary.zscore", "fields": {"col": {
                "type": "DIRECT", "op": "binary.minimum", "fields": {
                    "left": {"type": "DIRECT", "op": "binary.maximum", "fields": {
                        "left": "midcap_residual", "right": {"type": "CS", "op": "unary.quantile", "fields": {"col": "midcap_residual"}, "params": {"q": 0.025, "interpolation": "lower"}, "on": "market_valid"},
                    }},
                    "right": {"type": "CS", "op": "unary.quantile", "fields": {"col": "midcap_residual"}, "params": {"q": 0.975, "interpolation": "higher"}, "on": "market_valid"},
                },
            }}, "params": {"ddof": 1}, "on": "market_valid",
        },
    }
    for name, field in (("vsal_ttm", "revenue_ttm"), ("vern_ttm", "n_income_attr_p_ttm"), ("vflo_ttm", "n_incr_cash_cash_equ_ttm")):
        observed = {"type": "TS", "op": "unary.shift", "fields": {"col": field}, "params": {"periods": 1}}
        derivatives[name] = {
            "type": "TS", "op": "unary.ffill", "fields": {"col": {
                "type": "DIRECT", "op": "binary.div", "fields": {
                    side: {"type": "TS", "op": operation, "fields": {"col": observed},
                           "params": {"window": "5y", "min_periods": 3}, "on": "monthly_sample", "by": "sample_month"}
                    for side, operation in (("left", "unary.rolling_std"), ("right", "unary.rolling_mean"))
                },
            }},
        }
    for name, field, sign in (
        ("agro", "total_assets", -1.0), ("igro", "annual_share_sum", -1.0),
        ("cxgro", "capital_disposal", -1.0), ("egro_ttm", "earnings_per_share", 1.0),
        ("sgro_ttm", "sales_per_share", 1.0),
    ):
        observed = {"type": "TS", "op": "unary.shift", "fields": {"col": field}, "params": {"periods": 1}}
        derivatives[name] = {
            "type": "TS", "op": "unary.ffill", "fields": {"col": {
                "type": "DIRECT", "op": "binary.mul", "fields": {
                    "left": sign, "right": {"type": "DIRECT", "op": "binary.div", "fields": {
                        "left": {"type": "TS", "op": "binary.rolling_beta", "fields": {"left": "sample_year", "right": observed}, "params": {"window": "5y", "min_periods": 3}, "on": "monthly_sample", "by": "sample_month"},
                        "right": {"type": "TS", "op": "unary.rolling_mean", "fields": {"col": observed}, "params": {"window": "5y", "min_periods": 3}, "on": "monthly_sample", "by": "sample_month"},
                    }},
                },
            }},
        }
    for name, numerator, denominator in (
        ("dtoa", "total_liab", "total_assets"),
        ("ato_ttm", "revenue_ttm", "total_assets"),
        ("roa_ttm", "n_income_attr_p_ttm", "total_assets"),
        ("btop", "total_hldr_eqy_inc_min_int", "market_cap"),
        ("cetop_ttm", "n_cashflow_act_ttm", "market_cap"),
        ("etop_ttm", "n_income_attr_p_ttm", "market_cap"),
        ("gp_ttm", "gross_profit", "total_assets"),
        ("gpm_ttm", "gross_profit", "revenue_ttm"),
        ("dtop", "dividend_yield", 100.0),
    ):
        derivatives[name] = {"type": "DIRECT", "op": "binary.div", "fields": {"left": numerator, "right": denominator}}
    for name, denominator in (("mlev", "market_cap"), ("blev", "total_hldr_eqy_inc_min_int")):
        derivatives[name] = {"type": "DIRECT", "op": "binary.add", "fields": {
            "left": 1.0, "right": {"type": "DIRECT", "op": "binary.div", "fields": {"left": "long_liability", "right": denominator}},
        }}
    # 沿用原getEm的计算方向：企业价值代理 / EBIT，而不是把名称误解为其倒数。
    derivatives["em"] = {"type": "DIRECT", "op": "binary.div", "fields": {
        "left": {"type": "DIRECT", "op": "binary.sub", "fields": {"left": "market_cap", "right": "cash_equivalents"}},
        "right": "earnings_before_interest",
    }}
    for name, window, multiplier in (("stom", 21, 1.0), ("stoq", 63, 3.0), ("stoa", "365d", 1.0 / 11)):
        derivatives[name] = {"type": "DIRECT", "op": "unary.log", "fields": {"col": {
            "type": "DIRECT", "op": "binary.mul", "fields": {
                "left": multiplier, "right": {"type": "TS", "op": "unary.rolling_sum", "fields": {"col": {
                    "type": "DIRECT", "op": "binary.div", "fields": {"left": "turnover_rate", "right": 100.0},
                }}, "params": {"window": window, "min_periods": 1}},
            },
        }}}
    derivatives["atvr"] = {"type": "TS", "op": "unary.rolling_mean", "fields": {"col": "turnover_rate"}, "params": {"window": 252, "min_periods": 252, "weights": window_weights(252, 63)}}
    # 官方Cal按实际行情记录滚动；稠密日历中的停牌空行不占观测窗口，也不伪造零收益。
    for name, operation in (("hbeta", "binary.rolling_beta"), ("hsigma", "binary.rolling_residual_std")):
        derivatives[name] = {
            "type": "TS", "op": "unary.ffill", "fields": {"col": {
                "type": "TS", "op": operation,
                "fields": {"left": "benchmark_return", "right": "return_day"},
                "params": {"window": 252, "min_periods": 252, "method": "wls", "weights": window_weights(252, 63)},
                "on": "return_observed",
            }},
        }
    for name, window, lag, half_life, alpha in (
        ("rstr", 252, 11, 126, False), ("halpha", 252, 11, 126, True),
        ("ltrstr", 1040, 273, 260, False), ("lthalpha", 1040, 273, 260, True),
    ):
        rolling = {
            "type": "TS", "op": "binary.rolling_alpha" if alpha else "unary.rolling_mean",
            "fields": {"left": "benchmark_return", "right": "return_day"} if alpha else {"col": "log_relative_return"},
            "params": {"window": window, "min_periods": window, "weights": window_weights(window, half_life), **({"method": "wls"} if alpha else {})},
            "on": "return_observed",
        }
        derivatives[name] = {"type": "TS", "op": "unary.ffill", "fields": {"col": {
            "type": "TS", "op": "unary.rolling_mean", "fields": {"col": {
                "type": "TS", "op": "unary.shift", "fields": {"col": rolling},
                "params": {"periods": lag}, "on": "return_observed",
            }}, "params": {"window": 11, "min_periods": 11}, "on": "return_observed",
        }}}
    # Cal使用整段均值会依赖查询结束日；日频实现改为同窗加权方差，不引入未来信息。
    derivatives["dastd"] = {"type": "DIRECT", "op": "unary.sqrt", "fields": {"col": {
        "type": "DIRECT", "op": "binary.maximum", "fields": {"left": 0.0, "right": {
            "type": "DIRECT", "op": "binary.sub", "fields": {
                "left": {"type": "TS", "op": "unary.rolling_mean", "fields": {"col": {"type": "DIRECT", "op": "binary.pow", "fields": {"left": "excess_return", "right": 2.0}}}, "params": {"window": 252, "min_periods": 252, "weights": window_weights(252, 42)}},
                "right": {"type": "DIRECT", "op": "binary.pow", "fields": {"left": {"type": "TS", "op": "unary.rolling_mean", "fields": {"col": "excess_return"}, "params": {"window": 252, "min_periods": 252, "weights": window_weights(252, 42)}}, "right": 2.0}},
            },
        }},
    }}}
    cumulative = [{"type": "TS", "op": "unary.rolling_sum", "fields": {"col": {"type": "DIRECT", "op": "unary.log1p", "fields": {"col": "excess_return"}}}, "params": {"window": f"{month}M", "min_periods": 1}} for month in range(1, 13)]
    derivatives["cmra"] = {"type": "DIRECT", "op": "binary.sub", "fields": {
        "left": {"type": "DIRECT", "op": "multiary.max", "fields": {"cols": cumulative}},
        "right": {"type": "DIRECT", "op": "multiary.min", "fields": {"cols": cumulative}},
    }}
    if not cross_section:
        for name in ("scaled_float_month_sum", "midcap_residual", "midcap"):
            del derivatives[name]
    return FactorQuery(
        start_date=start.isoformat(), end_date=end.isoformat(), codes=codes,
        lookback=timedelta(days=config.history_years * 366),
        financial_max_age=timedelta(days=config.report_years * 366),
        factors=["close", "total_assets", "total_liab", "total_ncl", "total_cur_liab", "is_st"],
        derivatives=derivatives,
    )
