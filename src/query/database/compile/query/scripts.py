"""启动时编译无服务器模块依赖的 query 会话脚本。"""

import json
from functools import cache
from pathlib import Path

from query.database.compile import build_script as compile_script
from query.database.compile.script import write_script as write_compiled_script

from .functions import QUERY_FUNCTIONS

QUERY_SCRIPT = r"""
def buildQuery(request) {
    sourceTable = loadTable(request.database, request.table)
    calendar = exec distinct timestamp(date(time)) from sourceTable
        where factor = `close, time >= request.start, time < request.end
        order by timestamp(date(time))
    if (size(calendar) == 0) throw "查询区间没有交易日历"

    timeline = calendar
    for (column in request.weights) {
        observedDates = exec distinct timestamp(time) from sourceTable
            where factor = symbol([column])[0], time >= request.start, time < request.end
        timeline = sort(distinct(timeline join observedDates))
    }
    source = build_factor_source(
        sourceTable,
        request.codes,
        request.factors,
        timeline,
        request.start,
        request.end
    )
    source[`selected] = source.time in calendar

    for (column in request.factors) {
        if (column == request.st) {
            source = fill_null_column(source, column, 0.0)
        } else if (column in request.weights) {
            observedDates = exec distinct timestamp(time) from sourceTable
                where factor = symbol([column])[0], time >= request.start, time < request.end
            source[column] = iif(
                source.time in observedDates,
                nullFill(source[column], 0.0),
                source[column]
            )
            source = forward_fill_column(source, column, source.code, source.time)
        } else if (column in request.financial || column in request.industry) {
            source = forward_fill_column(source, column, source.code, source.time)
        }
    }
    source = finalize_factor_source(source, request.factors)
    computed = compute_factors(source, fromStdJson(request.definitions))
    filtered = filter_factors(computed, request.filters)
    data = project_factor_output(filtered, request.columns, request.outputStart, request.outputEnd)
    calendar = calendar[calendar >= request.outputStart && calendar < request.outputEnd]
    return dict(`source`computed`filtered`data`calendar, [source, computed, filtered, data, calendar])
}
"""


@cache
def build_script() -> str:
    """一次编译全部查询函数及 common 依赖，供每个 session 预加载。"""
    from query.workers.industry import INDUSTRY_FACTORS
    from query.workers.stock_financial import FINANCIAL_FACTORS

    script = compile_script("query", QUERY_FUNCTIONS, uses=("ta",)) + "\n" + QUERY_SCRIPT
    return script.replace("__FINANCIAL_FACTORS__", json.dumps(sorted(FINANCIAL_FACTORS))).replace(
        "__INDUSTRY_FACTORS__", json.dumps(list(INDUSTRY_FACTORS))
    )


def write_script(*, output_dir: Path = Path("output")) -> Path:
    return write_compiled_script("query", build_script(), output_dir=output_dir)
