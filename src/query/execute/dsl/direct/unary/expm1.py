"""unary.expm1 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryExpm1Params(StrictModel):
    """unary.expm1 不接收参数。"""


class DirectUnaryExpm1Operator(DirectOperator):
    """逐行执行 expm1。"""

    op: Literal['unary.expm1'] = Field(..., description='逐行执行 expm1。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryExpm1Params = Field(
        default_factory=DirectUnaryExpm1Params,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
