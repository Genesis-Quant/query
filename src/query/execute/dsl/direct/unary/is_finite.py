"""unary.is_finite 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryIsFiniteParams(StrictModel):
    """unary.is_finite 不接收参数。"""


class DirectUnaryIsFiniteOperator(DirectOperator):
    """判断数值是否有限。"""

    op: Literal['unary.is_finite'] = Field(..., description='判断数值是否有限。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryIsFiniteParams = Field(
        default_factory=DirectUnaryIsFiniteParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
