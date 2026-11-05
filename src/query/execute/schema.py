"""统一导出查询请求、DSL 节点及其依赖解析。"""

from .dsl import (
    Derivative,
    FactorQuery,
)

QUERY_RESERVED_REFERENCES = frozenset({
    "coreQueryStart",
    "coreQueryEnd",
    "coreQueryCodes",
    "coreQueryFactors",
    "coreQueryDates",
    "coreDslDefinitionsJson",
    "coreDslFilters",
    "coreDslOutputColumns",
    "coreOutputStart",
    "coreOutputEnd",
    "queryRequest",
    "queryResult",
})

__all__ = [
    "Derivative",
    "FactorQuery",
    "QUERY_RESERVED_REFERENCES",
]
