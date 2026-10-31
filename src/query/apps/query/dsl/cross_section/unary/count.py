"""unary.count 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryCountParams(StrictModel):
    """unary.count 不接收参数。"""


class CrossSectionUnaryCountOperator(CrossSectionOperator):
    """按交易日广播 count 统计量。"""

    op: Literal['unary.count'] = Field(..., description='按交易日广播 count 统计量。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryCountParams = Field(
        default_factory=CrossSectionUnaryCountParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
