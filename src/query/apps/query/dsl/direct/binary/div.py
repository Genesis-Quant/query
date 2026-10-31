"""binary.div 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryDivParams(StrictModel):
    """binary.div 不接收参数。"""


class DirectBinaryDivOperator(DirectOperator):
    """逐行执行 div。"""

    op: Literal['binary.div'] = Field(..., description='逐行执行 div。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryDivParams = Field(
        default_factory=DirectBinaryDivParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
