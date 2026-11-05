"""unary.round 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryRoundParams(StrictModel):
    """unary.round 参数。"""

    precision: int = Field(default=0, ge=0, le=15, description="保留小数位数。")


class DirectUnaryRoundOperator(DirectOperator):
    """逐行四舍五入。"""

    op: Literal['unary.round'] = Field(..., description='逐行四舍五入。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryRoundParams = Field(
        default_factory=DirectUnaryRoundParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
