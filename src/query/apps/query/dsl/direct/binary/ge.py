"""binary.ge 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryGeParams(StrictModel):
    """binary.ge 不接收参数。"""


class DirectBinaryGeOperator(DirectOperator):
    """逐行比较 ge。"""

    op: Literal['binary.ge'] = Field(..., description='逐行比较 ge。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryGeParams = Field(
        default_factory=DirectBinaryGeParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
