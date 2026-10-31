"""纯规范化工具，以及按需加载的运行期工具。"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .normalize import (
    DateLike,
    normalize_date,
    normalize_date_range,
    normalize_str,
    normalize_str_list,
)
from .schema import (
    CODE_COLUMN,
    CORE_COLUMNS,
    FACTOR_COLUMN,
    IS_ST_FACTOR,
    TIME_COLUMN,
    VALUE_COLUMN,
    WEIGHT_PREFIX,
    index_weight_factor,
)
from .validation import (
    normalize_dolphindb_functions,
    validate_dolphindb_identifier,
    validate_dolphindb_references,
)

if TYPE_CHECKING:
    from .logging import logger
    from .result import SessionResult
    from .retry import Retry
    from .throttle import RateLimiter
    from .ts_api import (
        get_codes,
        get_stock_metadata,
    )

LAZY_EXPORTS = {
    "logger": ("query.utils.logging", "logger"),
    "SessionResult": ("query.utils.result", "SessionResult"),
    "RateLimiter": ("query.utils.throttle", "RateLimiter"),
    "Retry": ("query.utils.retry", "Retry"),
    "get_codes": ("query.utils.ts_api", "get_codes"),
    "get_stock_metadata": ("query.utils.ts_api", "get_stock_metadata"),
}

__all__ = [
    "CODE_COLUMN",
    "CORE_COLUMNS",
    "DateLike",
    "FACTOR_COLUMN",
    "IS_ST_FACTOR",
    "RateLimiter",
    "Retry",
    "SessionResult",
    "TIME_COLUMN",
    "VALUE_COLUMN",
    "WEIGHT_PREFIX",
    "get_codes",
    "get_stock_metadata",
    "index_weight_factor",
    "logger",
    "normalize_date",
    "normalize_date_range",
    "normalize_dolphindb_functions",
    "normalize_str",
    "normalize_str_list",
    "validate_dolphindb_identifier",
    "validate_dolphindb_references",
]


def __getattr__(name: str) -> Any:
    if name not in LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
