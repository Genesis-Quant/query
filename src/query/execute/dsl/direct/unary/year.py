"""unary.year 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryYearParams(StrictModel):
    """unary.year 不接收参数。"""


class DirectUnaryYearOperator(DirectOperator):
    """提取或判断日期属性 year。"""

    op: Literal['unary.year'] = Field(..., description='提取或判断日期属性 year。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryYearParams = Field(
        default_factory=DirectUnaryYearParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
