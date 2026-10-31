"""提供 DolphinDB 标识符和函数定义的公共校验。"""

import re
from collections.abc import Mapping
from textwrap import dedent
from typing import Any

DOLPHINDB_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
DOLPHINDB_FUNCTION_PATTERN = re.compile(
    r"^def\s+([A-Za-z][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*\{",
    re.MULTILINE,
)
DOLPHINDB_CALLBACK_PARAMETER_PATTERN = re.compile(
    r"(?:(mutable)\s+)?([A-Za-z][A-Za-z0-9_]*)"
)


def validate_dolphindb_identifier(value: Any, location: str = "DolphinDB 变量名") -> str:
    """校验可安全插入 DOS 的 DolphinDB 标识符。"""
    if not isinstance(value, str) or DOLPHINDB_IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{location} 不是合法的 DolphinDB 标识符：{value!r}")
    return value


def validate_dolphindb_references(
        references: Mapping[str, Any],
        *,
        reserved: set[str] | frozenset[str] = frozenset(),
) -> None:
    """校验一组 DolphinDB 引用，并拒绝重复值和内部保留名称。"""
    values = [validate_dolphindb_identifier(value, name) for name, value in references.items()]
    if len(values) != len(set(values)):
        raise ValueError(f"DolphinDB 引用不能重复：{dict(references)}")
    if conflicts := sorted(set(values) & reserved):
        raise ValueError(f"DolphinDB 引用不能使用内部保留名称：{conflicts}")


def parse_dolphindb_function(definition: Any, location: str = "definition") -> tuple[str, str, str]:
    """整理 DolphinDB def 定义并返回源码、函数名和参数签名。"""
    if not isinstance(definition, str):
        raise ValueError(f"{location} 必须是字符串")
    normalized = dedent(definition).strip()
    match = DOLPHINDB_FUNCTION_PATTERN.match(normalized)
    if match is None:
        raise ValueError(f"{location} 必须以完整的 DolphinDB def 函数定义开头")
    depth = 0
    quote = ""
    offset = match.end() - 1
    function_end = None
    while offset < len(normalized):
        character = normalized[offset]
        if quote:
            if character == "\\":
                offset += 2
                continue
            if character == quote:
                quote = ""
            offset += 1
            continue
        if character in {'"', "'"}:
            quote = character
            offset += 1
            continue
        if normalized.startswith("//", offset):
            line_end = normalized.find("\n", offset + 2)
            offset = len(normalized) if line_end < 0 else line_end + 1
            continue
        if normalized.startswith("/*", offset):
            comment_end = normalized.find("*/", offset + 2)
            if comment_end < 0:
                raise ValueError(f"{location} 包含未结束的块注释")
            offset = comment_end + 2
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                function_end = offset + 1
                break
        offset += 1
    if function_end is None:
        raise ValueError(f"{location} 包含未结束的 DolphinDB 函数定义")
    if normalized[function_end:].strip():
        raise ValueError(f"{location} 只能包含一个 DolphinDB def 函数定义")
    return normalized, match.group(1), match.group(2).strip()


def validate_dolphindb_callback_signature(
        signature: str,
        location: str,
        parameter_count: int,
) -> None:
    """校验固定生命周期回调的参数数量及 mutable context 参数。"""
    parameters = [] if not signature else [parameter.strip() for parameter in signature.split(",")]
    if len(parameters) != parameter_count:
        raise ValueError(f"{location} 必须定义 {parameter_count} 个参数，实际为 {len(parameters)} 个")
    names: list[str] = []
    for parameter in parameters:
        match = DOLPHINDB_CALLBACK_PARAMETER_PATTERN.fullmatch(parameter)
        if match is None:
            raise ValueError(f"{location} 包含无效参数声明：{parameter!r}")
        names.append(match.group(2))
    if len(names) != len(set(names)):
        raise ValueError(f"{location} 不能包含重复参数：{names}")
    if parameters and not parameters[0].startswith("mutable "):
        raise ValueError(f"{location} 的第一个参数必须声明为 mutable context")


def normalize_dolphindb_functions(
        definitions: Mapping[str, str] | None,
        location: str,
        *,
        parameter_counts: Mapping[str, int] | None = None,
) -> dict[str, str]:
    """整理 DolphinDB 函数定义，并要求映射键与实际函数名一致。"""
    if definitions is None:
        raise ValueError(f"{location} 不能为空")
    if not isinstance(definitions, Mapping):
        raise ValueError(f"{location} 必须是函数名到 DolphinDB def 定义的映射")
    if any(not isinstance(name, str) for name in definitions):
        raise ValueError(f"{location} 的函数名和定义必须都是字符串")
    if parameter_counts is not None:
        if unknown := sorted(set(definitions) - set(parameter_counts)):
            raise ValueError(f"{location} 包含不支持的固定函数名：{unknown}")
        if missing := [name for name in parameter_counts if name not in definitions]:
            raise ValueError(f"{location} 缺少固定函数：{missing}")
    result: dict[str, str] = {}
    names = parameter_counts if parameter_counts is not None else definitions
    for expected_name in names:
        definition = definitions[expected_name]
        definition_location = f"{location}[{expected_name!r}]"
        normalized, actual_name, signature = parse_dolphindb_function(definition, definition_location)
        if actual_name != expected_name:
            raise ValueError(f"{location}[{expected_name!r}] 定义的函数名是 {actual_name!r}")
        if parameter_counts is not None and expected_name in parameter_counts:
            validate_dolphindb_callback_signature(
                signature,
                definition_location,
                parameter_counts[expected_name],
            )
        result[expected_name] = normalized
    return result
