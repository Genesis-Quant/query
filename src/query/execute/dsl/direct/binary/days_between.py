"""binary.days_between 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectBinaryDaysBetweenParams(StrictModel):
    """binary.days_between 不接收参数。"""


class DirectBinaryDaysBetweenOperator(DirectOperator):
    """计算两个日期相差天数。"""

    op: Literal['binary.days_between'] = Field(..., description='计算两个日期相差天数。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectBinaryDaysBetweenParams = Field(
        default_factory=DirectBinaryDaysBetweenParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
