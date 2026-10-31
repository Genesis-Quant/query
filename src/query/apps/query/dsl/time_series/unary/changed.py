"""unary.changed 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryChangedParams(StrictModel):
    """unary.changed 参数。"""

    null_equal: bool = Field(default=False, description="两个连续 NULL 是否视为相等。")


class TimeSeriesUnaryChangedOperator(TimeSeriesOperator):
    """判断是否不同于上一条 on=true 观测。"""

    op: Literal['unary.changed'] = Field(..., description='判断是否不同于上一条 on=true 观测。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryChangedParams = Field(
        default_factory=TimeSeriesUnaryChangedParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
