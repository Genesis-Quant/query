"""unary.kurt 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryKurtParams(StrictModel):
    """unary.kurt 不接收参数。"""


class CrossSectionUnaryKurtOperator(CrossSectionOperator):
    """按交易日广播 kurt 统计量。"""

    op: Literal['unary.kurt'] = Field(..., description='按交易日广播 kurt 统计量。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryKurtParams = Field(
        default_factory=CrossSectionUnaryKurtParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
