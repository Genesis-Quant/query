"""按依赖顺序编译可直接在 session 中运行的 DolphinDB 函数。"""

from collections.abc import Iterable
from pathlib import Path

from .function import DolphinDBFunction


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


def build_script(
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


def write_script(module: str, script: str, *, output_dir: Path) -> Path:
    path = output_dir / f"{module}.dos"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != script:
        path.write_text(script, encoding="utf-8", newline="\n")
    return path
