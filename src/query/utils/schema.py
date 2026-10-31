"""定义统一因子数据的列契约和指数权重 factor 命名规则。"""

import re

TIME_COLUMN = "time"
CODE_COLUMN = "code"
FACTOR_COLUMN = "factor"
VALUE_COLUMN = "value"
CORE_COLUMNS = (
    TIME_COLUMN,
    CODE_COLUMN,
    FACTOR_COLUMN,
    VALUE_COLUMN,
)
IS_ST_FACTOR = "is_st"
WEIGHT_PREFIX = "weight_"


def index_weight_factor(index_code: str) -> str:
    """把指数代码转换为统一长表中的权重 factor 名。"""
    normalized = str(index_code).strip().upper()
    if re.fullmatch(r"[A-Z0-9]+\.[A-Z0-9]+", normalized) is None:
        raise ValueError(f"无效指数代码：{index_code!r}")
    return WEIGHT_PREFIX + normalized.replace(".", "")
