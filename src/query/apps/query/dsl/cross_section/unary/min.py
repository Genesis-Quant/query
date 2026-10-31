"""unary.min 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryMinParams(StrictModel):
    """unary.min 不接收参数。"""


class CrossSectionUnaryMinOperator(CrossSectionOperator):
    """按交易日广播 min 统计量。"""

    op: Literal['unary.min'] = Field(..., description='按交易日广播 min 统计量。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryMinParams = Field(
        default_factory=CrossSectionUnaryMinParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
