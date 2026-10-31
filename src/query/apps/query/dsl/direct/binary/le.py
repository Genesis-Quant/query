"""binary.le 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryLeParams(StrictModel):
    """binary.le 不接收参数。"""


class DirectBinaryLeOperator(DirectOperator):
    """逐行比较 le。"""

    op: Literal['binary.le'] = Field(..., description='逐行比较 le。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryLeParams = Field(
        default_factory=DirectBinaryLeParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
