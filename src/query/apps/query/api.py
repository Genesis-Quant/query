"""在指定 DolphinDB 因子窄表执行 DSL，不加载服务器上的 query 模块。"""

import json
import sys
from datetime import timedelta
from typing import Any

import numpy as np

from query.database.session import create_session, initialize_session, redirect_session_output
from query.settings import DolphinSettings
from query.utils import (
    IS_ST_FACTOR,
    WEIGHT_PREFIX,
    get_codes,
    logger,
    normalize_date_range,
    normalize_str_list,
    validate_dolphindb_references,
)
from query.workers import available_factors
from query.workers.industry import INDUSTRY_FACTORS
from query.workers.stock_financial import FINANCIAL_FACTORS

from .result import QueryResult
from .schema import QUERY_RESERVED_REFERENCES, FactorQuery

SOURCE_REF = "coreQuerySourceData"
COMPUTED_REF = "coreQueryComputedData"
FILTERED_REF = "coreQueryFilteredData"
DATA_REF = "coreQueryData"
CALENDAR_REF = "coreQueryCalendar"


def validate_factor_query(request: FactorQuery | dict[str, Any]) -> FactorQuery:
    if isinstance(request, FactorQuery):
        return request
    if isinstance(request, dict):
        return FactorQuery.model_validate(request)
    raise TypeError("request 必须是 FactorQuery 或 dict[str, Any]")


def query_parameters(request: FactorQuery | dict[str, Any], settings: DolphinSettings) -> dict[str, Any]:
    validated = validate_factor_query(request)
    start, end = normalize_date_range(validated.start_date, validated.end_date)
    factors = validated.source_factors()
    codes = validated.codes or list(get_codes())
    if not codes:
        raise ValueError("查询证券列表为空")
    return {
        "database": settings.database,
        "table": settings.table,
        "start": (start - validated.lookback).normalize(),
        "end": (end + validated.lookforward).normalize() + timedelta(days=1),
        "outputStart": start,
        "outputEnd": end + timedelta(days=1),
        "codes": np.asarray(codes, dtype=str),
        "factors": np.asarray(factors, dtype=str),
        "industry": np.asarray([name for name in factors if name in INDUSTRY_FACTORS], dtype=str),
        "financial": np.asarray([name for name in factors if name in FINANCIAL_FACTORS], dtype=str),
        "weights": np.asarray([name for name in factors if name.startswith(WEIGHT_PREFIX)], dtype=str),
        "st": IS_ST_FACTOR,
        "definitions": json.dumps({name: node.model_dump(mode="json") for name, node in validated.derivatives.items()}, ensure_ascii=False, separators=(",", ":")),
        "filters": np.asarray(validated.filters, dtype=str),
        "columns": np.asarray(["time", "code", *validated.factors, *validated.derivatives], dtype=str),
    }


def build_query_table(
    request: FactorQuery | dict[str, Any],
    *,
    session: Any,
    settings: DolphinSettings | None = None,
    source_ref: str = SOURCE_REF,
    computed_ref: str = COMPUTED_REF,
    filtered_ref: str = FILTERED_REF,
    data_ref: str = DATA_REF,
    calendar_ref: str = CALENDAR_REF,
    log_progress: bool = True,
) -> list[str]:
    references = dict(source_ref=source_ref, computed_ref=computed_ref, filtered_ref=filtered_ref,
                      data_ref=data_ref, calendar_ref=calendar_ref)
    validate_dolphindb_references(references, reserved=QUERY_RESERVED_REFERENCES)
    selected = settings if settings is not None else DolphinSettings.from_env()
    parameters = query_parameters(request, selected)
    initialize_session(session)
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
            session.run('if ("queryRequest" in objs(true).name) undef("queryRequest", VAR); if ("queryResult" in objs(true).name) undef("queryResult", VAR); NULL')
        except Exception as error:
            if not failed:
                raise
            logger.warning(f"查询失败后清理临时对象异常：{type(error).__name__}")
    return parameters["columns"].tolist()


def execute_query(
    request: FactorQuery | dict[str, Any],
    *,
    session: Any | None = None,
    settings: DolphinSettings | None = None,
) -> QueryResult:
    validated = validate_factor_query(request)
    selected = settings if settings is not None else DolphinSettings.from_env()
    owns_session = session is None
    current = create_session(selected) if owns_session else session
    references = (SOURCE_REF, COMPUTED_REF, FILTERED_REF, DATA_REF, CALENDAR_REF)
    started = False
    try:
        redirect_session_output(current)
        names = json.dumps(list(references))
        current.run(f'if (any({names} in objs(true).name)) throw "当前连接仍有未关闭的查询结果，请先关闭再查询"; NULL')
        started = True
        build_query_table(validated, session=current, settings=selected)
        return QueryResult(session=current, source_ref=SOURCE_REF, computed_ref=COMPUTED_REF,
                           filtered_ref=FILTERED_REF, data_ref=DATA_REF,
                           calendar_ref=CALENDAR_REF, owns_session=owns_session)
    except BaseException:
        try:
            if owns_session:
                current.close()
            elif started:
                QueryResult(session=current, source_ref=SOURCE_REF, computed_ref=COMPUTED_REF,
                            filtered_ref=FILTERED_REF, data_ref=DATA_REF,
                            calendar_ref=CALENDAR_REF, owns_session=False).close()
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
    settings: DolphinSettings | None = None,
    log_progress: bool = True,
) -> list[str]:
    build_query_table(request, session=session, settings=settings, source_ref=source_ref,
                      computed_ref=computed_ref, filtered_ref=filtered_ref, data_ref=data_ref,
                      log_progress=log_progress)
    values = session.run(f"exec distinct string(code) from {data_ref} where !isNull(code) order by code")
    if not isinstance(values, np.ndarray) or values.ndim != 1:
        raise TypeError("codes_query 必须返回一维代码向量")
    codes = normalize_str_list(values.astype(str).tolist(), "codes_query", reject_duplicates=True)
    if not codes:
        raise ValueError("codes_query 没有选出任何股票")
    return codes


__all__ = ["FactorQuery", "QueryResult", "available_factors", "build_query_table", "execute_query", "query_parameters"]
