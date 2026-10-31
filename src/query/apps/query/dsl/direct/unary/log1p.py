"""unary.log1p 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryLog1pParams(StrictModel):
    """unary.log1p 不接收参数。"""


class DirectUnaryLog1pOperator(DirectOperator):
    """逐行执行 log1p。"""

    op: Literal['unary.log1p'] = Field(..., description='逐行执行 log1p。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryLog1pParams = Field(
        default_factory=DirectUnaryLog1pParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
