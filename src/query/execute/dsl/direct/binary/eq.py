"""binary.eq 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryEqParams(StrictModel):
    """binary.eq 不接收参数。"""


class DirectBinaryEqOperator(DirectOperator):
    """逐行比较 eq。"""

    op: Literal['binary.eq'] = Field(..., description='逐行比较 eq。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryEqParams = Field(
        default_factory=DirectBinaryEqParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
