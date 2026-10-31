"""binary.minimum 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryMinimumParams(StrictModel):
    """binary.minimum 不接收参数。"""


class DirectBinaryMinimumOperator(DirectOperator):
    """逐行执行 minimum。"""

    op: Literal['binary.minimum'] = Field(..., description='逐行执行 minimum。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryMinimumParams = Field(
        default_factory=DirectBinaryMinimumParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
