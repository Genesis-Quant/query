"""binary.ne 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryNeParams(StrictModel):
    """binary.ne 不接收参数。"""


class DirectBinaryNeOperator(DirectOperator):
    """逐行比较 ne。"""

    op: Literal['binary.ne'] = Field(..., description='逐行比较 ne。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryNeParams = Field(
        default_factory=DirectBinaryNeParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
