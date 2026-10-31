"""unary.is_weekend 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryIsWeekendParams(StrictModel):
    """unary.is_weekend 不接收参数。"""


class DirectUnaryIsWeekendOperator(DirectOperator):
    """提取或判断日期属性 is_weekend。"""

    op: Literal['unary.is_weekend'] = Field(..., description='提取或判断日期属性 is_weekend。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryIsWeekendParams = Field(
        default_factory=DirectUnaryIsWeekendParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
