"""binary.maximum 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryMaximumParams(StrictModel):
    """binary.maximum 不接收参数。"""


class DirectBinaryMaximumOperator(DirectOperator):
    """逐行执行 maximum。"""

    op: Literal['binary.maximum'] = Field(..., description='逐行执行 maximum。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryMaximumParams = Field(
        default_factory=DirectBinaryMaximumParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
