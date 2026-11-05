"""binary.floor_div 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryFloorDivParams(StrictModel):
    """binary.floor_div 不接收参数。"""


class DirectBinaryFloorDivOperator(DirectOperator):
    """逐行执行 floor_div。"""

    op: Literal['binary.floor_div'] = Field(..., description='逐行执行 floor_div。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryFloorDivParams = Field(
        default_factory=DirectBinaryFloorDivParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
