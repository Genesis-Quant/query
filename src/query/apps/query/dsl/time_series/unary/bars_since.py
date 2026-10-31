"""unary.bars_since 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import BoolUnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryBarsSinceParams(StrictModel):
    """unary.bars_since 不接收参数。"""


class TimeSeriesUnaryBarsSinceOperator(TimeSeriesOperator):
    """计算距最近 true 的观测数。"""

    op: Literal['unary.bars_since'] = Field(..., description='计算距最近 true 的观测数。')
    fields: BoolUnaryFields = Field(..., description="该算符严格定义的 BOOL 输入字段。")
    params: TimeSeriesUnaryBarsSinceParams = Field(
        default_factory=TimeSeriesUnaryBarsSinceParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
