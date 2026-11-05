"""按依赖顺序编译可直接在 session 中运行的 DolphinDB 函数。"""

import json
from collections.abc import Iterable
from functools import cache
from pathlib import Path

from .functions import QUERY_FUNCTIONS
from .functions.function import DolphinDBFunction


def collect_functions(
    functions: Iterable[DolphinDBFunction],
    module: str | None = None,
) -> tuple[DolphinDBFunction, ...]:
    """跨原模块内联全部依赖，拒绝重名、冲突定义和循环。"""
    ordered: list[DolphinDBFunction] = []
    definitions: dict[str, DolphinDBFunction] = {}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(current: DolphinDBFunction) -> None:
        existing = definitions.get(current.name)
        if existing is not None and existing != current:
            raise ValueError(f"DolphinDB 函数 {current.name!r} 重复定义")
        definitions[current.name] = current
        if current.name in visited:
            return
        if current.name in visiting:
            raise ValueError(f"DolphinDB 函数依赖存在循环：{current.name}")
        visiting.add(current.name)
        for dependency in current.dependencies:
            visit(dependency)
        visiting.remove(current.name)
        visited.add(current.name)
        ordered.append(current)

    for function in functions:
        if module is not None and function.module != module:
            raise ValueError(f"根函数 {function.name!r} 不属于 {module!r}")
        visit(function)
    return tuple(ordered)


def render_functions(functions: Iterable[DolphinDBFunction]) -> str:
    definitions = "\n\n".join(function.definition for function in functions)
    return f"{definitions}\n" if definitions else ""


def compile_functions(
    module: str,
    functions: Iterable[DolphinDBFunction],
    *,
    uses: Iterable[str] = (),
) -> str:
    """生成会话脚本；不声明 module，也不加载服务器上的 query/common。"""
    compiled = collect_functions(functions, module)
    imports = tuple(uses)
    if any(name != "ta" for name in imports):
        raise ValueError("会话脚本仅允许引入 DolphinDB 内置 ta 模块")
    statements = [f"use {name}" for name in sorted(set(imports))]
    statements.append(render_functions(compiled).rstrip())
    return "\n\n".join(statements).rstrip() + "\n"


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
    """编译查询函数及其依赖，供调用方显式初始化已有会话。"""
    from query.workers.core.industry import INDUSTRY_FACTORS
    from query.workers.core.stock_financial import FINANCIAL_FACTORS

    source = compile_functions("query", QUERY_FUNCTIONS, uses=("ta",)) + "\n" + QUERY_SCRIPT
    return source.replace("__FINANCIAL_FACTORS__", json.dumps(sorted(FINANCIAL_FACTORS))).replace(
        "__INDUSTRY_FACTORS__", json.dumps(list(INDUSTRY_FACTORS))
    )


def write_script(*, output_dir: Path = Path("output")) -> Path:
    path = output_dir / "query.dos"
    path.parent.mkdir(parents=True, exist_ok=True)
    source = build_script()
    if not path.exists() or path.read_text(encoding="utf-8") != source:
        path.write_text(source, encoding="utf-8", newline="\n")
    return path
