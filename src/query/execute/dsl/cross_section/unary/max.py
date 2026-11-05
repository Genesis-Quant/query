"""unary.max 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryMaxParams(StrictModel):
    """unary.max 不接收参数。"""


class CrossSectionUnaryMaxOperator(CrossSectionOperator):
    """按交易日广播 max 统计量。"""

    op: Literal['unary.max'] = Field(..., description='按交易日广播 max 统计量。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryMaxParams = Field(
        default_factory=CrossSectionUnaryMaxParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
