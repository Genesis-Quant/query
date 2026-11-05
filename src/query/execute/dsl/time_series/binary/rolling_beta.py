"""binary.rolling_beta 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    RegressionWeights,
    StrictModel,
    Window,
    validate_regression_weights,
)


class TimeSeriesBinaryRollingBetaParams(StrictModel):
    """binary.rolling_beta 参数。"""

    window: Window = Field(..., description="整数为观测条数；字符串为日历窗口，如21d、12M、5y。")
    min_periods: int | None = Field(default=None, ge=1, description="产生结果所需的最少共同有效观测数。")
    method: Literal["ols", "wls"] = Field(default="ols", description="窗口回归方法；默认等权OLS。")
    weights: RegressionWeights | None = Field(default=None, description="WLS窗口位置权重，从旧到新；短窗口对齐末端，0权重行保留有效残差。")

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesBinaryRollingBetaParams":
        """确保最少观测数不超过窗口。"""
        if isinstance(self.window, int) and self.min_periods is not None and self.min_periods > self.window:
            raise ValueError("params.min_periods 不能大于 params.window")
        validate_regression_weights(self.window, self.method, self.weights)
        return self


class TimeSeriesBinaryRollingBetaOperator(TimeSeriesOperator):
    """按股票执行 rolling_beta。"""

    op: Literal['binary.rolling_beta'] = Field(..., description='按股票执行 rolling_beta。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesBinaryRollingBetaParams = Field(
        default_factory=TimeSeriesBinaryRollingBetaParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
