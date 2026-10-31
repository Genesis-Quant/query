"""unary.is_year_end 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryIsYearEndParams(StrictModel):
    """unary.is_year_end 不接收参数。"""


class DirectUnaryIsYearEndOperator(DirectOperator):
    """提取或判断日期属性 is_year_end。"""

    op: Literal['unary.is_year_end'] = Field(..., description='提取或判断日期属性 is_year_end。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryIsYearEndParams = Field(
        default_factory=DirectUnaryIsYearEndParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
