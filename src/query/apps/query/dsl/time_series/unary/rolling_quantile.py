"""unary.rolling_quantile 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryRollingQuantileParams(StrictModel):
    """unary.rolling_quantile 参数。"""

    window: int = Field(..., ge=1, description="on=true 序列中的窗口长度。")
    min_periods: int | None = Field(default=None, ge=1, description="产生结果所需的最少非空观测数。")
    q: float = Field(..., ge=0, le=1, allow_inf_nan=False, description="目标分位数。")

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesUnaryRollingQuantileParams":
        """确保最少观测数不超过窗口。"""
        if self.min_periods is not None and self.min_periods > self.window:
            raise ValueError("params.min_periods 不能大于 params.window")
        return self


class TimeSeriesUnaryRollingQuantileOperator(TimeSeriesOperator):
    """按股票计算滚动分位数。"""

    op: Literal['unary.rolling_quantile'] = Field(..., description='按股票计算滚动分位数。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryRollingQuantileParams = Field(
        default_factory=TimeSeriesUnaryRollingQuantileParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
