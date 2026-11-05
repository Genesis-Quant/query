"""unary.quarter 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryQuarterParams(StrictModel):
    """unary.quarter 不接收参数。"""


class DirectUnaryQuarterOperator(DirectOperator):
    """提取或判断日期属性 quarter。"""

    op: Literal['unary.quarter'] = Field(..., description='提取或判断日期属性 quarter。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryQuarterParams = Field(
        default_factory=DirectUnaryQuarterParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
