"""unary.weekday 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryWeekdayParams(StrictModel):
    """unary.weekday 不接收参数。"""


class DirectUnaryWeekdayOperator(DirectOperator):
    """提取或判断日期属性 weekday。"""

    op: Literal['unary.weekday'] = Field(..., description='提取或判断日期属性 weekday。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryWeekdayParams = Field(
        default_factory=DirectUnaryWeekdayParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
