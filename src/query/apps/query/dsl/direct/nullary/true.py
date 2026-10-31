"""nullary.true 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import NullaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectNullaryTrueParams(StrictModel):
    """nullary.true 不接收参数。"""


class DirectNullaryTrueOperator(DirectOperator):
    """广播 true。"""

    op: Literal['nullary.true'] = Field(..., description='广播 true。')
    fields: NullaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectNullaryTrueParams = Field(
        default_factory=DirectNullaryTrueParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
