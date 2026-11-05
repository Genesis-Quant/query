"""binary.sub 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinarySubParams(StrictModel):
    """binary.sub 不接收参数。"""


class DirectBinarySubOperator(DirectOperator):
    """逐行执行 sub。"""

    op: Literal['binary.sub'] = Field(..., description='逐行执行 sub。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinarySubParams = Field(
        default_factory=DirectBinarySubParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
