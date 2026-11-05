"""unary.mean 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryMeanParams(StrictModel):
    """unary.mean 不接收参数。"""


class CrossSectionUnaryMeanOperator(CrossSectionOperator):
    """按交易日广播 mean 统计量。"""

    op: Literal['unary.mean'] = Field(..., description='按交易日广播 mean 统计量。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryMeanParams = Field(
        default_factory=CrossSectionUnaryMeanParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
