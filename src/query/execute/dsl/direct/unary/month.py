"""unary.month 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryMonthParams(StrictModel):
    """unary.month 不接收参数。"""


class DirectUnaryMonthOperator(DirectOperator):
    """提取或判断日期属性 month。"""

    op: Literal['unary.month'] = Field(..., description='提取或判断日期属性 month。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryMonthParams = Field(
        default_factory=DirectUnaryMonthParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
