"""unary.rolling_mean 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    RegressionWeights,
    StrictModel,
    Window,
    validate_regression_weights,
)


class TimeSeriesUnaryRollingMeanParams(StrictModel):
    """unary.rolling_mean 参数。"""

    window: Window = Field(..., description="整数为观测条数；字符串为日历窗口，如21d、12M、5y。")
    min_periods: int | None = Field(default=None, ge=1, description="产生结果所需的最少非空观测数。")
    weights: RegressionWeights | None = Field(default=None, description="可选有限窗口位置权重，从旧到新；不提供时保留等权均值。")

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesUnaryRollingMeanParams":
        """确保最少观测数不超过窗口。"""
        if isinstance(self.window, int) and self.min_periods is not None and self.min_periods > self.window:
            raise ValueError("params.min_periods 不能大于 params.window")
        if self.weights is not None:
            validate_regression_weights(self.window, "wls", self.weights)
        return self


class TimeSeriesUnaryRollingMeanOperator(TimeSeriesOperator):
    """按股票执行 rolling_mean。"""

    op: Literal['unary.rolling_mean'] = Field(..., description='按股票执行 rolling_mean。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryRollingMeanParams = Field(
        default_factory=TimeSeriesUnaryRollingMeanParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
