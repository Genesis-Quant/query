"""unary.is_null 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryIsNullParams(StrictModel):
    """unary.is_null 不接收参数。"""


class DirectUnaryIsNullOperator(DirectOperator):
    """判断是否为空。"""

    op: Literal['unary.is_null'] = Field(..., description='判断是否为空。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryIsNullParams = Field(
        default_factory=DirectUnaryIsNullParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
