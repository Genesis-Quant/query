"""nullary.false 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import NullaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectNullaryFalseParams(StrictModel):
    """nullary.false 不接收参数。"""


class DirectNullaryFalseOperator(DirectOperator):
    """广播 false。"""

    op: Literal['nullary.false'] = Field(..., description='广播 false。')
    fields: NullaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectNullaryFalseParams = Field(
        default_factory=DirectNullaryFalseParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
