"""unary.demean 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryDemeanParams(StrictModel):
    """unary.demean 不接收参数。"""


class CrossSectionUnaryDemeanOperator(CrossSectionOperator):
    """按交易日执行 demean。"""

    op: Literal['unary.demean'] = Field(..., description='按交易日执行 demean。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryDemeanParams = Field(
        default_factory=CrossSectionUnaryDemeanParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
