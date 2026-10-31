"""binary.lt 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryLtParams(StrictModel):
    """binary.lt 不接收参数。"""


class DirectBinaryLtOperator(DirectOperator):
    """逐行比较 lt。"""

    op: Literal['binary.lt'] = Field(..., description='逐行比较 lt。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryLtParams = Field(
        default_factory=DirectBinaryLtParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
