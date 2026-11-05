"""unary.asin 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryAsinParams(StrictModel):
    """unary.asin 不接收参数。"""


class DirectUnaryAsinOperator(DirectOperator):
    """逐行执行 asin。"""

    op: Literal['unary.asin'] = Field(..., description='逐行执行 asin。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryAsinParams = Field(
        default_factory=DirectUnaryAsinParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
