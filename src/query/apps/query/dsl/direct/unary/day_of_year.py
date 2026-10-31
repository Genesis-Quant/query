"""unary.day_of_year 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryDayOfYearParams(StrictModel):
    """unary.day_of_year 不接收参数。"""


class DirectUnaryDayOfYearOperator(DirectOperator):
    """提取或判断日期属性 day_of_year。"""

    op: Literal['unary.day_of_year'] = Field(..., description='提取或判断日期属性 day_of_year。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryDayOfYearParams = Field(
        default_factory=DirectUnaryDayOfYearParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
