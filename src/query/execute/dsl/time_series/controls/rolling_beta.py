"""controls.rolling_beta 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import ControlsFields
from query.execute.dsl.types import (
    OutputKind,
    RegressionFill,
    RegressionFillMethod,
    RegressionWeights,
    StrictModel,
    Window,
    validate_regression_weights,
)


class TimeSeriesControlsRollingBetaParams(StrictModel):
    """多元滚动 OLS/WLS 系数参数。"""

    window: Window = Field(..., description="整数为观测条数；字符串为日历窗口，如21d、12M、5y。")
    min_periods: int | None = Field(default=None, ge=1, description="输入填充后的最少共同有效样本数；整数窗口默认window，日历窗口默认1。")
    method: Literal["ols", "wls"] = Field(default="ols", description="窗口回归方法；默认等权OLS。")
    weights: RegressionWeights | None = Field(default=None, description="WLS窗口位置权重，从旧到新；短窗口对齐末端，0权重行保留有效残差。")
    intercept: bool = Field(default=True, description="回归是否包含截距。")
    index: int = Field(default=0, ge=0, description="0 起算的当前窗口展开列索引，不含截距；分类按类别升序删除首类，不存在的索引返回 NULL。")
    fill: RegressionFillMethod = Field(default="ffill", description="填充规则：None 不填，ffill 默认前向填充，mean 同日截面均值，或 constant/逐列配置。")

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesControlsRollingBetaParams":
        if isinstance(self.window, int) and self.min_periods is not None and self.min_periods > self.window:
            raise ValueError("params.min_periods 不能大于 params.window")
        validate_regression_weights(self.window, self.method, self.weights)
        return self


class TimeSeriesControlsRollingBetaOperator(TimeSeriesOperator):
    """以 controls 解释 target，返回指定变量的同窗 SVD OLS 系数。"""

    op: Literal["controls.rolling_beta"] = Field(..., description="多元滚动 OLS 的指定解释变量系数。")
    fields: ControlsFields = Field(..., description="数值目标与有序的连续或 BOOL/STRING/SYMBOL 分类解释变量；默认各列 ffill 后共同排除仍缺失的行。")
    params: TimeSeriesControlsRollingBetaParams = Field(default_factory=TimeSeriesControlsRollingBetaParams)
    output_kind: ClassVar[OutputKind] = "NUMBER"

    @model_validator(mode="after")
    def validate_fill_controls(self) -> "TimeSeriesControlsRollingBetaOperator":
        fill = self.params.fill
        if isinstance(fill, RegressionFill) and fill.controls is not None:
            if len(fill.controls) != len(self.fields.controls):
                raise ValueError("params.fill.controls 必须与 fields.controls 等长")
        return self
