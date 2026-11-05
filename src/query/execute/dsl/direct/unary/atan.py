"""unary.atan 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryAtanParams(StrictModel):
    """unary.atan 不接收参数。"""


class DirectUnaryAtanOperator(DirectOperator):
    """逐行执行 atan。"""

    op: Literal['unary.atan'] = Field(..., description='逐行执行 atan。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryAtanParams = Field(
        default_factory=DirectUnaryAtanParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
