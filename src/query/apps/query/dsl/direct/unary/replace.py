"""unary.replace 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    JsonScalar,
    OutputKind,
    StrictModel,
)


class DirectUnaryReplaceParams(StrictModel):
    """unary.replace 参数。"""

    old: list[JsonScalar] = Field(..., min_length=1, description="待替换常量列表。")
    new: list[JsonScalar] = Field(..., min_length=1, description="替换后常量列表。")

    @model_validator(mode="after")
    def validate_lengths(self) -> "DirectUnaryReplaceParams":
        """确保替换前后列表等长。"""
        if len(self.old) != len(self.new):
            raise ValueError("params.old 与 params.new 必须等长")
        return self


class DirectUnaryReplaceOperator(DirectOperator):
    """按常量列表替换值。"""

    op: Literal['unary.replace'] = Field(..., description='按常量列表替换值。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryReplaceParams = Field(
        default_factory=DirectUnaryReplaceParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'ANY'
