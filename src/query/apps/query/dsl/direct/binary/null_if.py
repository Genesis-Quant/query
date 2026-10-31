"""binary.null_if 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryNullIfParams(StrictModel):
    """binary.null_if 不接收参数。"""


class DirectBinaryNullIfOperator(DirectOperator):
    """相等时返回 NULL。"""

    op: Literal['binary.null_if'] = Field(..., description='相等时返回 NULL。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryNullIfParams = Field(
        default_factory=DirectBinaryNullIfParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'ANY'
