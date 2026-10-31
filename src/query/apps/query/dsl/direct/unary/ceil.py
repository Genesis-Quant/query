"""unary.ceil 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryCeilParams(StrictModel):
    """unary.ceil 不接收参数。"""


class DirectUnaryCeilOperator(DirectOperator):
    """逐行执行 ceil。"""

    op: Literal['unary.ceil'] = Field(..., description='逐行执行 ceil。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryCeilParams = Field(
        default_factory=DirectUnaryCeilParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
