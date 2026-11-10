"""在指定 DolphinDB 因子窄表执行 DSL，不加载服务器上的 query 模块。"""

import json
import sys
from datetime import timedelta
from typing import Any

import numpy as np

from query.config import DolphinSettings
from query.database.compile.script import build_script
from query.utils import (
    IS_ST_FACTOR,
    WEIGHT_PREFIX,
    get_codes,
    logger,
    normalize_date_range,
    normalize_str_list,
    validate_dolphindb_references,
)

from .result import QueryResult
from .schema import QUERY_RESERVED_REFERENCES, FactorQuery

SOURCE_REF = "coreQuerySourceData"
COMPUTED_REF = "coreQueryComputedData"
FILTERED_REF = "coreQueryFilteredData"
DATA_REF = "coreQueryData"
CALENDAR_REF = "coreQueryCalendar"


def initialize_query(session: Any) -> None:
    """由调用方显式注入Query DOS；查询过程中不检查、不记忆或自动初始化。"""
    if session is None:
        raise TypeError("session 必须是已有的 DolphinDB 会话")
    session.run(build_script())


def validate_factor_query(request: FactorQuery | dict[str, Any]) -> FactorQuery:
    if isinstance(request, FactorQuery):
        return request
    if isinstance(request, dict):
        return FactorQuery.model_validate(request)
    raise TypeError("request 必须是 FactorQuery 或 dict[str, Any]")


def query_parameters(
        request: FactorQuery | dict[str, Any], settings: type[DolphinSettings] = DolphinSettings,
) -> dict[str, Any]:
    from query.workers.core.industry import INDUSTRY_FACTORS
    from query.workers.core.stock_financial import FINANCIAL_FACTORS

    validated = validate_factor_query(request)
    start, end = normalize_date_range(validated.start_date, validated.end_date)
    factors = validated.source_factors()
    codes = validated.codes or list(get_codes())
    if not codes:
        raise ValueError("查询证券列表为空")
    return {
        "database": settings.core_database,
        "table": settings.core_table,
        "start": (start - validated.lookback).normalize(),
        "end": (end + validated.lookforward).normalize() + timedelta(days=1),
        "outputStart": start,
        "outputEnd": end + timedelta(days=1),
        "codes": np.asarray(codes, dtype=str),
        "factors": np.asarray(factors, dtype=str),
        "industry": np.asarray([name for name in factors if name in INDUSTRY_FACTORS], dtype=str),
        "financial": np.asarray([name for name in factors if name in FINANCIAL_FACTORS], dtype=str),
        "financialMaxAge": np.int64(-1 if validated.financial_max_age is None else validated.financial_max_age.days),
        "weights": np.asarray([name for name in factors if name.startswith(WEIGHT_PREFIX)], dtype=str),
        "st": IS_ST_FACTOR,
        "definitions": json.dumps({name: node.model_dump(mode="json") for name, node in validated.derivatives.items()},
                                  ensure_ascii=False, separators=(",", ":")),
        "filters": np.asarray(validated.filters, dtype=str),
        "columns": np.asarray(["time", "code", *validated.factors, *validated.derivatives], dtype=str),
    }


def build_query_table(
        request: FactorQuery | dict[str, Any],
        *,
        session: Any,
        settings: type[DolphinSettings] = DolphinSettings,
        source_ref: str = SOURCE_REF,
        computed_ref: str = COMPUTED_REF,
        filtered_ref: str = FILTERED_REF,
        data_ref: str = DATA_REF,
        calendar_ref: str = CALENDAR_REF,
) -> list[str]:
    references = dict(source_ref=source_ref, computed_ref=computed_ref, filtered_ref=filtered_ref,
                      data_ref=data_ref, calendar_ref=calendar_ref)
    validate_dolphindb_references(references, reserved=QUERY_RESERVED_REFERENCES)
    parameters = query_parameters(request, settings)
    session.upload({"queryRequest": parameters})
    try:
        session.run(f"""
            queryResult = buildQuery(queryRequest)
            {source_ref} = queryResult.source
            {computed_ref} = queryResult.computed
            {filtered_ref} = queryResult.filtered
            {data_ref} = queryResult.data
            {calendar_ref} = queryResult.calendar
            NULL
        """)
    finally:
        failed = sys.exception() is not None
        try:
            session.run(
                'if ("queryRequest" in objs(true).name) undef("queryRequest", VAR); if ("queryResult" in objs(true).name) undef("queryResult", VAR); NULL')
        except Exception as error:
            if not failed:
                raise
            logger.warning(f"查询失败后清理临时对象异常：{type(error).__name__}")
    return parameters["columns"].tolist()


def execute_query(
        request: FactorQuery | dict[str, Any],
        *,
        session: Any,
        settings: type[DolphinSettings] = DolphinSettings,
) -> QueryResult:
    """使用调用方已显式初始化的会话；不注入DOS、不关闭连接。"""
    if session is None:
        raise TypeError("session 必须是已有的 DolphinDB 会话")
    validated = validate_factor_query(request)
    references = (SOURCE_REF, COMPUTED_REF, FILTERED_REF, DATA_REF, CALENDAR_REF)
    started = False
    try:
        names = json.dumps(list(references))
        session.run(f'if (any({names} in objs(true).name)) throw "当前连接仍有未关闭的查询结果，请先关闭再查询"; NULL')
        started = True
        build_query_table(validated, session=session, settings=settings)
        return QueryResult(session=session, source_ref=SOURCE_REF, computed_ref=COMPUTED_REF,
                           filtered_ref=FILTERED_REF, data_ref=DATA_REF,
                           calendar_ref=CALENDAR_REF)
    except BaseException:
        try:
            if started:
                QueryResult(session=session, source_ref=SOURCE_REF, computed_ref=COMPUTED_REF,
                            filtered_ref=FILTERED_REF, data_ref=DATA_REF,
                            calendar_ref=CALENDAR_REF).close()
        except Exception as error:
            logger.warning(f"查询失败后回收结果异常：{type(error).__name__}")
        raise


def execute_codes_query(
        request: FactorQuery | dict[str, Any],
        *,
        session: Any,
        source_ref: str,
        computed_ref: str,
        filtered_ref: str,
        data_ref: str,
        settings: type[DolphinSettings] = DolphinSettings,
) -> list[str]:
    build_query_table(
        request,
        session=session,
        settings=settings,
        source_ref=source_ref,
        computed_ref=computed_ref,
        filtered_ref=filtered_ref,
        data_ref=data_ref
    )
    values = session.run(f"exec distinct string(code) from {data_ref} where !isNull(code) order by code")
    if not isinstance(values, np.ndarray) or values.ndim != 1:
        raise TypeError("codes_query 必须返回一维代码向量")
    codes = normalize_str_list(values.astype(str).tolist(), "codes_query", reject_duplicates=True)
    if not codes:
        raise ValueError("codes_query 没有选出任何股票")
    return codes


__all__ = ["execute_query", "initialize_query"]
