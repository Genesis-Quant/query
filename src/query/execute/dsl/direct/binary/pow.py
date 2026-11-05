"""binary.pow 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryPowParams(StrictModel):
    """binary.pow 不接收参数。"""


class DirectBinaryPowOperator(DirectOperator):
    """逐行执行 pow。"""

    op: Literal['binary.pow'] = Field(..., description='逐行执行 pow。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryPowParams = Field(
        default_factory=DirectBinaryPowParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
