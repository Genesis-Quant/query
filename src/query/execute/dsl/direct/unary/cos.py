"""unary.cos 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryCosParams(StrictModel):
    """unary.cos 不接收参数。"""


class DirectUnaryCosOperator(DirectOperator):
    """逐行执行 cos。"""

    op: Literal['unary.cos'] = Field(..., description='逐行执行 cos。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryCosParams = Field(
        default_factory=DirectUnaryCosParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
