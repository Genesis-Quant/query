"""unary.expanding_quantile 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryExpandingQuantileParams(StrictModel):
    """unary.expanding_quantile 参数。"""

    min_periods: int = Field(default=1, ge=1, description="产生结果所需的最少非空观测数。")
    q: float = Field(..., ge=0, le=1, allow_inf_nan=False, description="目标分位数。")


class TimeSeriesUnaryExpandingQuantileOperator(TimeSeriesOperator):
    """按股票计算扩展分位数。"""

    op: Literal['unary.expanding_quantile'] = Field(..., description='按股票计算扩展分位数。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryExpandingQuantileParams = Field(
        default_factory=TimeSeriesUnaryExpandingQuantileParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
