"""查询、CoreData Worker 和 Barra Worker 的统一配置。"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path.cwd() / ".env")

INDEX_CODES = tuple(
    code.strip() for code in os.getenv(
        "INDEX_CODES", "000016.SH,000300.SH,000905.SH,000852.SH,000985.CSI"
    ).split(",") if code.strip()
)
DATA_START_DATE = os.getenv("DATA_START_DATE", "2010-01-01")
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")


class DolphinSettings:
    """查询及写入目标表位置，不包含连接端点或账号凭据。"""
    core_database = os.getenv("DOLPHIN_CORE_DATABASE", "dfs://CoreData")
    core_table = os.getenv("DOLPHIN_CORE_TABLE", "coreTable")
    barra_database = os.getenv("DOLPHIN_BARRA_DATABASE", "dfs://Barra")
    barra_table = os.getenv("DOLPHIN_BARRA_TABLE", "barra")
    barra_cov_table = os.getenv("DOLPHIN_BARRA_COV_TABLE", "barraCov")
    barra_sp_table = os.getenv("DOLPHIN_BARRA_SP_TABLE", "barraSp")
    snapshot_database = os.getenv("DOLPHIN_SNAPSHOT_DATABASE", "dfs://StockSnapshot")
    snapshot_table = os.getenv("DOLPHIN_SNAPSHOT_TABLE", "snapshot")


class WorkerSettings(DolphinSettings):
    """独立Query命令行更新所需的SDK连接配置，不供查询API建连。"""

    endpoints = tuple(
        endpoint.strip() for endpoint in os.getenv(
            "DOLPHINDB_ENDPOINTS",
            f"{os.getenv('DOLPHIN_HOST', 'dolphindb')}:{os.getenv('DOLPHIN_PORT', '8848')}",
        ).split(",") if endpoint.strip()
    )
    username = os.getenv("DOLPHINDB_USERNAME") or os.getenv("DOLPHIN_RUNTIME_USERNAME")
    password = os.getenv("DOLPHINDB_PASSWORD") or os.getenv("DOLPHIN_RUNTIME_PASSWORD")
    worker_username = os.getenv("DOLPHINDB_WORKER_USERNAME") or os.getenv("DOLPHIN_WORKER_USERNAME")
    worker_password = os.getenv("DOLPHINDB_WORKER_PASSWORD") or os.getenv("DOLPHIN_WORKER_PASSWORD")


class BarraConfig:
    """教程因子关系及已确认的日频参数；同样直接传递配置类。"""

    start_date = "2016-01-01"
    benchmark = "000985.CSI"
    industry_level = 1
    financial_page_size = 10_000
    first_factors = {
        "Quality": ["Earnings_Quality", "Earnings_Variability", "Investment_Quality",
                    "Leverage", "Profitability"],
        "Value": ["Btop", "Earning_Yield", "Long_Term_Reversal"],
        "Growth": ["Growth"],
        "Liquidity": ["Liquidity"],
        "Volatility": ["Beta", "Residual_Volatility"],
        "Size": ["Size", "Mid_Cap"],
        "Momentum": ["Momentum"],
        "Dividend_Yield": ["Dividend_Yield"],
    }
    second_factors = {
        "Earnings_Quality": ["abs", "acf_ttm"],
        "Earnings_Variability": ["vsal_ttm", "vern_ttm", "vflo_ttm"],
        "Investment_Quality": ["agro", "igro", "cxgro"],
        "Leverage": ["mlev", "dtoa", "blev"],
        "Profitability": ["ato_ttm", "gp_ttm", "gpm_ttm", "roa_ttm"],
        "Btop": ["btop"],
        "Earning_Yield": ["cetop_ttm", "etop_ttm", "em"],
        "Long_Term_Reversal": ["ltrstr", "lthalpha"],
        "Growth": ["egro_ttm", "sgro_ttm"],
        "Liquidity": ["stom", "stoq", "stoa", "atvr"],
        "Beta": ["hbeta"],
        "Residual_Volatility": ["hsigma", "dastd", "cmra"],
        "Size": ["lncap"],
        "Mid_Cap": ["midcap"],
        "Momentum": ["rstr", "halpha"],
        "Dividend_Yield": ["dtop"],
    }
    styles = tuple(first_factors)
    covariance_window = 252
    specific_window = 252
    covariance_half_life = 63.0
    specific_half_life = 63.0
    newey_west_lags = 5
    specific_shrinkage = True
    eigen_adjustment = False
    min_listing_days = 60
    min_specific_observations = 60
    specific_peer_fallback = True
    specific_peer_min_stocks = 5
    specific_short_observations = 20
    variance_floor = 1e-8
    history_years = 6
    report_years = 2
    price_window = 1324
    minimum_factor_coverage = 0.5
    minimum_stocks = 40
    minimum_risk_observations = 60
    exposure_limit = 5.0
