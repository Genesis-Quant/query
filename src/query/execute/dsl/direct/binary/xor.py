"""binary.xor 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import BoolBinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryXorParams(StrictModel):
    """binary.xor 不接收参数。"""


class DirectBinaryXorOperator(DirectOperator):
    """逐行逻辑 xor。"""

    op: Literal['binary.xor'] = Field(..., description='逐行逻辑 xor。')
    fields: BoolBinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryXorParams = Field(
        default_factory=DirectBinaryXorParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
