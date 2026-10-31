"""nullary.literal 算符模型。"""

import re
from datetime import datetime
from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import NullaryFields
from query.apps.query.dsl.types import (
    JsonScalar,
    OutputKind,
    StrictModel,
)


class DirectNullaryLiteralParams(StrictModel):
    """nullary.literal 参数。"""

    value: JsonScalar = Field(..., description="需要广播的 JSON 标量。")
    dtype: Literal[
        "bool", "int", "long", "float", "double", "string", "symbol", "date", "timestamp"
    ] | None = Field(default=None, description="显式 DolphinDB 类型；字符串日期和 NULL 建议指定。")

    @model_validator(mode="after")
    def validate_literal(self) -> "DirectNullaryLiteralParams":
        """校验 NULL 和日期字面量具有可确定类型。"""
        if self.value is None and self.dtype is None:
            raise ValueError("NULL 字面量必须指定 params.dtype")
        if self.value is None:
            return self
        if self.dtype not in {"date", "timestamp"}:
            return self
        if not isinstance(self.value, str):
            raise ValueError(f"dtype={self.dtype!r} 时 params.value 必须是字符串")
        if self.dtype == "date":
            try:
                datetime.strptime(self.value, "%Y-%m-%d")
            except ValueError as error:
                raise ValueError("dtype='date' 时 params.value 必须为 YYYY-MM-DD") from error
            return self
        if re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?"
            r"(?:Z|[+-]\d{2}:\d{2})?",
            self.value,
        ) is None:
            raise ValueError(
                "dtype='timestamp' 时 params.value 必须为 "
                "YYYY-MM-DDTHH:MM:SS 或带三位毫秒"
            )
        try:
            parsed = datetime.fromisoformat(self.value)
        except ValueError as error:
            raise ValueError("dtype='timestamp' 时 params.value 必须为 ISO 8601 时间") from error
        if parsed.tzinfo is not None:
            raise ValueError("DolphinDB TIMESTAMP 字面量不能包含时区")
        return self


class DirectNullaryLiteralOperator(DirectOperator):
    """广播一个显式类型的字面量。"""

    op: Literal['nullary.literal'] = Field(..., description='广播一个显式类型的字面量。')
    fields: NullaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectNullaryLiteralParams = Field(
        default_factory=DirectNullaryLiteralParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'ANY'
