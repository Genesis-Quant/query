"""unary.log10 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryLog10Params(StrictModel):
    """unary.log10 不接收参数。"""


class DirectUnaryLog10Operator(DirectOperator):
    """逐行执行 log10。"""

    op: Literal['unary.log10'] = Field(..., description='逐行执行 log10。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryLog10Params = Field(
        default_factory=DirectUnaryLog10Params,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
