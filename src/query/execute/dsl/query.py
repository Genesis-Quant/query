"""定义统一因子查询请求及其依赖解析。"""

import re
from datetime import date, timedelta
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializeAsAny,
    TypeAdapter,
    field_validator,
    model_validator,
)

from query.utils import normalize_date_range, normalize_str_list

from .derivative import Derivative, derivative_output_kind
from .fields import BoolBinaryFields, BoolMultiaryFields, BoolUnaryFields, TernaryFields

RESERVED_NAMES = frozenset(("time", "code"))


def validate_iso_date(value: Any, location: str) -> str:
    """校验严格的 YYYY-MM-DD 日期字符串。"""
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError(f"{location} 必须是 YYYY-MM-DD 格式的日期字符串")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{location} 不是有效日期：{value!r}") from error
    return value


def derivative_references(
        derivative: Derivative,
) -> tuple[set[str], set[str], set[str]]:
    """返回全部字符串引用，以及 on 和逻辑操作数使用的引用。"""
    references: set[str] = set()
    on_references: set[str] = set()
    bool_references: set[str] = set()

    def visit_operand(value: Any) -> None:
        """递归收集 fields 中的列名和命名派生因子引用。"""
        if isinstance(value, str):
            references.add(value)
        elif isinstance(value, Derivative):
            visit_derivative(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit_operand(item)

    def visit_derivative(value: Derivative) -> None:
        """收集一个节点的 fields，并单独记录字符串 on。"""
        for field_name in type(value.fields).model_fields.keys():
            visit_operand(getattr(value.fields, field_name))
        visit_operand(getattr(value, "by", None))
        on = getattr(value, "on", None)
        if isinstance(on, str):
            references.add(on)
            on_references.add(on)
        elif isinstance(on, Derivative):
            visit_derivative(on)

        bool_values: list[Any] = []
        if isinstance(value.fields, BoolUnaryFields):
            bool_values.append(value.fields.col)
        elif isinstance(value.fields, BoolBinaryFields):
            bool_values.extend((value.fields.left, value.fields.right))
        elif isinstance(value.fields, BoolMultiaryFields):
            bool_values.extend(value.fields.cols)
        elif isinstance(value.fields, TernaryFields):
            bool_values.append(value.fields.condition)
        bool_references.update(item for item in bool_values if isinstance(item, str))

    visit_derivative(derivative)
    return references, on_references, bool_references


class FactorQuery(BaseModel):
    """统一因子查询和可选 DSL 计算参数。"""

    model_config = ConfigDict(extra="forbid", strict=True)

    start_date: str = Field(
        ...,
        description="查询闭区间开始日期，格式为 YYYY-MM-DD。",
        examples=["2025-01-01"],
    )

    end_date: str = Field(
        ...,
        description="查询闭区间结束日期，格式为 YYYY-MM-DD。",
        examples=["2025-12-31"],
    )

    lookback: timedelta = Field(
        default=timedelta(0),
        ge=timedelta(0),
        description="计算前额外加载的历史时长；结果仍从 start_date 开始返回。",
        examples=["30D", "P30D"],
    )

    lookforward: timedelta = Field(
        default=timedelta(0),
        ge=timedelta(0),
        description="计算时额外加载的未来日历时长；结果和日历仍裁回原始闭区间。",
        examples=["P20D"],
    )

    codes: list[str] = Field(
        ...,
        description="需要查询的股票代码；空列表表示全市场。",
        examples=[["000001.SZ", "600000.SH"]],
    )

    factors: list[str] = Field(
        default_factory=list,
        description="需要直接输出的数据库 factor。",
        examples=[["close", "is_st", "weight_000300SH"]],
    )

    derivatives: dict[str, SerializeAsAny[Derivative]] = Field(
        default_factory=dict,
        description="需要在 DolphinDB 中计算并输出的命名派生因子。",
    )

    filters: list[str] = Field(
        default_factory=list,
        description="仅返回所有 BOOL 命名派生因子均为 true 的行。",
    )

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date(cls, value: str, info: Any) -> str:
        return validate_iso_date(value, info.field_name)

    @field_validator("lookback", "lookforward", mode="before")
    @classmethod
    def parse_duration(cls, value: Any, info: Any) -> timedelta:
        """接受 timedelta 或 Pydantic TimeDelta 字符串。"""
        if isinstance(value, timedelta):
            result = value
        elif isinstance(value, str):
            try:
                result = TypeAdapter(timedelta).validate_python(value)
            except ValueError as error:
                raise ValueError(
                    f"{info.field_name} 不是有效 TimeDelta：{value!r}"
                ) from error
        else:
            raise ValueError(f"{info.field_name} 必须是 timedelta 或 TimeDelta 字符串")
        if result < timedelta(0):
            raise ValueError(f"{info.field_name} 不能小于 0")
        return result

    @model_validator(mode="after")
    def validate_query(self) -> "FactorQuery":
        """规范名称并校验字段、引用、过滤类型和派生依赖关系。"""
        normalize_date_range(self.start_date, self.end_date)
        self.codes = normalize_str_list(self.codes, "codes", reject_duplicates=True)
        self.factors = normalize_str_list(self.factors, "factors", reject_duplicates=True)
        self.filters = normalize_str_list(self.filters, "filters", reject_duplicates=True)

        normalized_derivatives: dict[str, Derivative] = {}
        for name, derivative in self.derivatives.items():
            normalized = name.strip()
            if not normalized:
                raise ValueError("derivatives 不能包含空名称")
            if normalized in normalized_derivatives:
                raise ValueError(
                    f"derivatives 名称去除首尾空格后重复：{normalized!r}"
                )
            normalized_derivatives[normalized] = derivative
        self.derivatives = normalized_derivatives

        if not self.factors and not self.derivatives:
            raise ValueError("factors 和 derivatives 至少提供一项")
        if invalid := set(self.factors) & RESERVED_NAMES:
            raise ValueError(f"factors 不能使用保留名称：{sorted(invalid)}")
        if invalid := set(self.derivatives) & RESERVED_NAMES:
            raise ValueError(
                f"derivatives 不能使用保留名称：{sorted(invalid)}"
            )
        if overlap := set(self.factors) & set(self.derivatives):
            raise ValueError(
                f"factors 与 derivatives 名称冲突：{sorted(overlap)}"
            )

        derivative_names = set(self.derivatives)
        if missing_filters := set(self.filters) - derivative_names:
            raise ValueError(
                "filters 只能引用已定义的 BOOL 命名派生因子，"
                f"不存在：{sorted(missing_filters)}"
            )
        if non_bool_filters := [
            name for name in self.filters
            if derivative_output_kind(self.derivatives[name]) != "BOOL"
        ]:
            raise ValueError(
                "filters 对应命名派生因子必须返回 BOOL："
                f"{sorted(non_bool_filters)}"
            )

        dependencies: dict[str, set[str]] = {}
        for name, derivative in self.derivatives.items():
            references, on_references, bool_references = derivative_references(derivative)
            if missing_on := on_references - derivative_names:
                raise ValueError(
                    f"derivatives[{name!r}] 的 on 只能引用已定义的 BOOL "
                    f"命名派生因子，不存在：{sorted(missing_on)}"
                )
            if non_bool_on := [
                reference for reference in on_references
                if derivative_output_kind(self.derivatives[reference]) != "BOOL"
            ]:
                raise ValueError(
                    f"derivatives[{name!r}] 的 on 引用必须返回 BOOL："
                    f"{sorted(non_bool_on)}"
                )
            if non_bool_operands := [
                reference for reference in bool_references
                if reference not in derivative_names
                or derivative_output_kind(self.derivatives[reference]) != "BOOL"
            ]:
                raise ValueError(
                    f"derivatives[{name!r}] 的逻辑操作数引用必须返回 BOOL："
                    f"{sorted(non_bool_operands)}"
                )
            dependencies[name] = references & derivative_names

        states: dict[str, int] = {}
        path: list[str] = []

        def visit(n: str) -> None:
            """深度优先检查命名派生因子的直接或间接循环引用。"""
            state = states.get(n, 0)
            if state == 2:
                return
            if state == 1:
                start = path.index(n)
                cycle = [*path[start:], n]
                raise ValueError(
                    "derivatives 存在循环依赖：" + " -> ".join(cycle)
                )
            states[n] = 1
            path.append(n)
            for dependency in dependencies[n]:
                visit(dependency)
            path.pop()
            states[n] = 2

        for name in self.derivatives:
            visit(name)
        return self

    def source_factors(self) -> list[str]:
        """返回原始输出列与派生依赖的有序并集。"""
        references: set[str] = set()

        for derivative in self.derivatives.values():
            derivative_inputs = derivative_references(derivative)[0]
            references.update(derivative_inputs)
        references -= set(self.derivatives) | RESERVED_NAMES
        return normalize_str_list(
            [*self.factors, *sorted(references - set(self.factors))],
            "factors",
        )
