"""独立因子查询、会话编译和数据更新包。"""

from importlib import import_module
from typing import Any

from .apps.query.schema import Derivative, FactorQuery
from .settings import DolphinSettings

__all__ = ["Derivative", "DolphinSettings", "FactorQuery", "compile", "create_session", "execute_query", "query"]


def __getattr__(name: str) -> Any:
    exports = {
        "compile": ("query.database.compile.query.scripts", "build_script"),
        "create_session": ("query.database.session", "create_session"),
        "execute_query": ("query.apps.query.api", "execute_query"),
        "query": ("query.apps.query.api", "execute_query"),
    }
    if name not in exports:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = exports[name]
    value = getattr(import_module(module), attribute)
    globals()[name] = value
    return value
