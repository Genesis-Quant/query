"""binary.mul 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryMulParams(StrictModel):
    """binary.mul 不接收参数。"""


class DirectBinaryMulOperator(DirectOperator):
    """逐行执行 mul。"""

    op: Literal['binary.mul'] = Field(..., description='逐行执行 mul。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryMulParams = Field(
        default_factory=DirectBinaryMulParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
