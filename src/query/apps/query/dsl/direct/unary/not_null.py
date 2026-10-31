"""unary.not_null 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryNotNullParams(StrictModel):
    """unary.not_null 不接收参数。"""


class DirectUnaryNotNullOperator(DirectOperator):
    """判断是否非空。"""

    op: Literal['unary.not_null'] = Field(..., description='判断是否非空。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryNotNullParams = Field(
        default_factory=DirectUnaryNotNullParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
