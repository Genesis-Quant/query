"""unary.tan 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryTanParams(StrictModel):
    """unary.tan 不接收参数。"""


class DirectUnaryTanOperator(DirectOperator):
    """逐行执行 tan。"""

    op: Literal['unary.tan'] = Field(..., description='逐行执行 tan。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryTanParams = Field(
        default_factory=DirectUnaryTanParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
