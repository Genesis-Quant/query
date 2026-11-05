"""unary.get 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryGetParams(StrictModel):
    """unary.get 不接收参数。"""


class DirectUnaryGetOperator(DirectOperator):
    """原样返回操作数。"""

    op: Literal['unary.get'] = Field(..., description='原样返回操作数。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryGetParams = Field(
        default_factory=DirectUnaryGetParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'ANY'
