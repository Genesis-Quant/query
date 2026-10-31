"""unary.exp 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryExpParams(StrictModel):
    """unary.exp 不接收参数。"""


class DirectUnaryExpOperator(DirectOperator):
    """逐行执行 exp。"""

    op: Literal['unary.exp'] = Field(..., description='逐行执行 exp。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryExpParams = Field(
        default_factory=DirectUnaryExpParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
