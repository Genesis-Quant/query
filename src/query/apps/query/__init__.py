"""因子查询模型与按需加载的执行接口。"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .schema import Derivative, FactorQuery

if TYPE_CHECKING:
    from .api import execute_query

LAZY_EXPORTS = {
    "execute_query": ("query.apps.query.api", "execute_query"),
}

__all__ = ["Derivative", "FactorQuery", "execute_query"]


def __getattr__(name: str) -> Any:
    if name not in LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
