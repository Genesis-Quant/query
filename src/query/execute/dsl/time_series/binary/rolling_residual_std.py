"""binary.rolling_residual_std 算符模型。"""

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


class TimeSeriesBinaryRollingResidualStdParams(StrictModel):
    """以left解释right，计算当前窗口同一次拟合的残差样本标准差。"""

    window: Window = Field(..., description="整数为观测条数；字符串为日历窗口，如21d、12M、5y。")
    min_periods: int | None = Field(default=None, ge=1, description="最少共同有效观测数；整数窗口默认window，日历窗口默认1。")
    method: Literal["ols", "wls"] = Field(default="ols", description="窗口回归方法；默认等权OLS。")
    weights: RegressionWeights | None = Field(default=None, description="WLS窗口位置权重，从旧到新；短窗口对齐末端，0权重行保留有效残差。")

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesBinaryRollingResidualStdParams":
        if isinstance(self.window, int) and self.min_periods is not None and self.min_periods > self.window:
            raise ValueError("params.min_periods 不能大于 params.window")
        validate_regression_weights(self.window, self.method, self.weights)
        return self


class TimeSeriesBinaryRollingResidualStdOperator(TimeSeriesOperator):
    """当前窗口中right对left拟合一次后取残差std(ddof=1)，自变量无方差时为NULL。"""

    op: Literal["binary.rolling_residual_std"] = Field(..., description="当前窗口整组拟合残差的样本标准差；不是回归标准误或加权标准差。")
    fields: BinaryFields = Field(..., description="left为数值自变量，right为数值因变量；共同排除无效观测，不填充输入。")
    params: TimeSeriesBinaryRollingResidualStdParams = Field(default_factory=TimeSeriesBinaryRollingResidualStdParams)
    output_kind: ClassVar[OutputKind] = "NUMBER"
