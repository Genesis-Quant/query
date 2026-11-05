"""unary.log2 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryLog2Params(StrictModel):
    """unary.log2 不接收参数。"""


class DirectUnaryLog2Operator(DirectOperator):
    """逐行执行 log2。"""

    op: Literal['unary.log2'] = Field(..., description='逐行执行 log2。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryLog2Params = Field(
        default_factory=DirectUnaryLog2Params,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
