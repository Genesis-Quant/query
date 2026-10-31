"""binary.and 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import BoolBinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryAndParams(StrictModel):
    """binary.and 不接收参数。"""


class DirectBinaryAndOperator(DirectOperator):
    """逐行逻辑 and。"""

    op: Literal['binary.and'] = Field(..., description='逐行逻辑 and。')
    fields: BoolBinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryAndParams = Field(
        default_factory=DirectBinaryAndParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
