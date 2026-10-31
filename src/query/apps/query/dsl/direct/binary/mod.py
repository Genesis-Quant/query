"""binary.mod 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryModParams(StrictModel):
    """binary.mod 不接收参数。"""


class DirectBinaryModOperator(DirectOperator):
    """逐行执行 mod。"""

    op: Literal['binary.mod'] = Field(..., description='逐行执行 mod。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryModParams = Field(
        default_factory=DirectBinaryModParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
