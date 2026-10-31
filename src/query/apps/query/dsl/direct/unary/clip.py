"""unary.clip 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryClipParams(StrictModel):
    """unary.clip 参数。"""

    lower: float | None = Field(default=None, allow_inf_nan=False, description="下界；省略表示无下界。")
    upper: float | None = Field(default=None, allow_inf_nan=False, description="上界；省略表示无上界。")

    @model_validator(mode="after")
    def validate_bounds(self) -> "DirectUnaryClipParams":
        """要求至少一个边界且上下界顺序正确。"""
        if self.lower is None and self.upper is None:
            raise ValueError("params.lower 与 params.upper 至少提供一个")
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("params.lower 不能大于 params.upper")
        return self


class DirectUnaryClipOperator(DirectOperator):
    """按常量边界逐行截断。"""

    op: Literal['unary.clip'] = Field(..., description='按常量边界逐行截断。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryClipParams = Field(
        default_factory=DirectUnaryClipParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
