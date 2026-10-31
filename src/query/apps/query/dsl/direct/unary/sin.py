"""unary.sin 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnarySinParams(StrictModel):
    """unary.sin 不接收参数。"""


class DirectUnarySinOperator(DirectOperator):
    """逐行执行 sin。"""

    op: Literal['unary.sin'] = Field(..., description='逐行执行 sin。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnarySinParams = Field(
        default_factory=DirectUnarySinParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
