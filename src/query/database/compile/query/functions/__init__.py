"""汇总 query DolphinDB 模块需要编译的函数。"""

from .cross_section import CROSS_SECTION_OPERATOR_FUNCTIONS
from .direct import DIRECT_OPERATOR_FUNCTIONS
from .dispatch import EVALUATOR_FUNCTIONS
from .runtime import (
    DERIVE_ENTRY_FUNCTIONS,
    DERIVE_HELPER_FUNCTIONS,
    TOOL_FUNCTIONS,
)
from .time_series import TIME_SERIES_OPERATOR_FUNCTIONS

OPERATOR_FUNCTIONS = (
    *sorted(DIRECT_OPERATOR_FUNCTIONS, key=lambda function: function.name),
    *sorted(TIME_SERIES_OPERATOR_FUNCTIONS, key=lambda function: function.name),
    *sorted(CROSS_SECTION_OPERATOR_FUNCTIONS, key=lambda function: function.name),
)
QUERY_FUNCTIONS = (
    *OPERATOR_FUNCTIONS,
    *TOOL_FUNCTIONS,
    *DERIVE_HELPER_FUNCTIONS,
    *EVALUATOR_FUNCTIONS,
    *DERIVE_ENTRY_FUNCTIONS,
)
