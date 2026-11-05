"""unary.neg 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryNegParams(StrictModel):
    """unary.neg 不接收参数。"""


class DirectUnaryNegOperator(DirectOperator):
    """逐行执行 neg。"""

    op: Literal['unary.neg'] = Field(..., description='逐行执行 neg。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryNegParams = Field(
        default_factory=DirectUnaryNegParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
