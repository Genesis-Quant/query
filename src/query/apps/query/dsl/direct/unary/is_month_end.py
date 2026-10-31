"""unary.is_month_end 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryIsMonthEndParams(StrictModel):
    """unary.is_month_end 不接收参数。"""


class DirectUnaryIsMonthEndOperator(DirectOperator):
    """提取或判断日期属性 is_month_end。"""

    op: Literal['unary.is_month_end'] = Field(..., description='提取或判断日期属性 is_month_end。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryIsMonthEndParams = Field(
        default_factory=DirectUnaryIsMonthEndParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
