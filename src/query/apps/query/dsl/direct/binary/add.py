"""binary.add 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryAddParams(StrictModel):
    """binary.add 不接收参数。"""


class DirectBinaryAddOperator(DirectOperator):
    """逐行执行 add。"""

    op: Literal['binary.add'] = Field(..., description='逐行执行 add。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryAddParams = Field(
        default_factory=DirectBinaryAddParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
