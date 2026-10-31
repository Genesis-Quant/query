"""unary.abs 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryAbsParams(StrictModel):
    """unary.abs 不接收参数。"""


class DirectUnaryAbsOperator(DirectOperator):
    """逐行执行 abs。"""

    op: Literal['unary.abs'] = Field(..., description='逐行执行 abs。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryAbsParams = Field(
        default_factory=DirectUnaryAbsParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
