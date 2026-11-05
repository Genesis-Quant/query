"""unary.day 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryDayParams(StrictModel):
    """unary.day 不接收参数。"""


class DirectUnaryDayOperator(DirectOperator):
    """提取或判断日期属性 day。"""

    op: Literal['unary.day'] = Field(..., description='提取或判断日期属性 day。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryDayParams = Field(
        default_factory=DirectUnaryDayParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
