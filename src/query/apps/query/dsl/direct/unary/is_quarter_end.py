"""unary.is_quarter_end 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryIsQuarterEndParams(StrictModel):
    """unary.is_quarter_end 不接收参数。"""


class DirectUnaryIsQuarterEndOperator(DirectOperator):
    """提取或判断日期属性 is_quarter_end。"""

    op: Literal['unary.is_quarter_end'] = Field(..., description='提取或判断日期属性 is_quarter_end。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryIsQuarterEndParams = Field(
        default_factory=DirectUnaryIsQuarterEndParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
