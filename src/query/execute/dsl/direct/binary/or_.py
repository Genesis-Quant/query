"""binary.or 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import BoolBinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryOrParams(StrictModel):
    """binary.or 不接收参数。"""


class DirectBinaryOrOperator(DirectOperator):
    """逐行逻辑 or。"""

    op: Literal['binary.or'] = Field(..., description='逐行逻辑 or。')
    fields: BoolBinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryOrParams = Field(
        default_factory=DirectBinaryOrParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
