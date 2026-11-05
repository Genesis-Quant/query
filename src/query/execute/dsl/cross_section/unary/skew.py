"""unary.skew 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnarySkewParams(StrictModel):
    """unary.skew 不接收参数。"""


class CrossSectionUnarySkewOperator(CrossSectionOperator):
    """按交易日广播 skew 统计量。"""

    op: Literal['unary.skew'] = Field(..., description='按交易日广播 skew 统计量。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnarySkewParams = Field(
        default_factory=CrossSectionUnarySkewParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
