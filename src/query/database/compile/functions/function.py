"""定义可组合、可按依赖编译的 DolphinDB 函数源码。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from query.utils.validation import parse_dolphindb_function

PARAMETER_PATTERN = re.compile(
    r"(?:mutable\s+)?([A-Za-z_][A-Za-z0-9_]*)(?:\s*=\s*.+)?"
)
MODULE_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*$"
)


@dataclass(frozen=True, slots=True)
class DolphinDBFunction:
    """保存一个 DolphinDB 函数及其直接依赖。"""

    definition: str
    dependencies: tuple[DolphinDBFunction, ...] = ()
    module: str | None = None
    name: str = field(init=False)
    parameters: tuple[str, ...] = field(init=False)
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        """从函数定义解析并校验名称和参数。"""
        definition, function_name, signature = parse_dolphindb_function(self.definition)

        raw_parameters = tuple(
            parameter.strip()
            for parameter in signature.split(",")
            if parameter.strip()
        )
        parameter_matches = [
            PARAMETER_PATTERN.fullmatch(parameter)
            for parameter in raw_parameters
        ]
        invalid = [
            parameter
            for parameter, parameter_match in zip(
                raw_parameters,
                parameter_matches,
                strict=True,
            )
            if parameter_match is None
        ]
        if invalid:
            raise ValueError(f"DolphinDB 函数参数名非法：{invalid}")
        parameters = tuple(
            parameter_match.group(1)
            for parameter_match in parameter_matches
            if parameter_match is not None
        )
        if len(parameters) != len(set(parameters)):
            raise ValueError(f"DolphinDB 函数 {function_name!r} 包含重复参数")

        dependency_keys = [
            (dependency.module, dependency.name)
            for dependency in self.dependencies
        ]
        if len(dependency_keys) != len(set(dependency_keys)):
            raise ValueError(f"DolphinDB 函数 {function_name!r} 包含重复依赖")
        if (
            self.module is not None
            and MODULE_PATTERN.fullmatch(self.module) is None
        ):
            raise ValueError(f"DolphinDB 模块名非法：{self.module!r}")

        object.__setattr__(self, "definition", definition)
        object.__setattr__(self, "name", function_name)
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "signature", signature)
