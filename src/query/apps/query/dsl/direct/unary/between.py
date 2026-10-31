"""unary.between 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryBetweenParams(StrictModel):
    """unary.between 参数。"""

    lower: float = Field(..., allow_inf_nan=False, description="区间下界。")
    upper: float = Field(..., allow_inf_nan=False, description="区间上界。")
    inclusive: Literal["both", "left", "right", "neither"] = Field(
        default="both", description="边界包含方式。"
    )

    @model_validator(mode="after")
    def validate_bounds(self) -> "DirectUnaryBetweenParams":
        """校验区间边界顺序。"""
        if self.lower > self.upper:
            raise ValueError("params.lower 不能大于 params.upper")
        return self


class DirectUnaryBetweenOperator(DirectOperator):
    """判断是否位于指定区间。"""

    op: Literal['unary.between'] = Field(..., description='判断是否位于指定区间。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryBetweenParams = Field(
        default_factory=DirectUnaryBetweenParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
