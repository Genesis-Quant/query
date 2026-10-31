"""unary.week 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryWeekParams(StrictModel):
    """unary.week 不接收参数。"""


class DirectUnaryWeekOperator(DirectOperator):
    """提取或判断日期属性 week。"""

    op: Literal['unary.week'] = Field(..., description='提取或判断日期属性 week。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryWeekParams = Field(
        default_factory=DirectUnaryWeekParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
