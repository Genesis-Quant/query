"""controls.rolling_residual 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import ControlsFields
from query.apps.query.dsl.types import OutputKind, StrictModel


class TimeSeriesControlsRollingResidualParams(StrictModel):
    """多元滚动 OLS 当前观测残差参数。"""

    window: int = Field(..., ge=1, description="on=true 序列中的右对齐窗口长度。")
    min_periods: int | None = Field(default=None, ge=1, description="最少共同有效样本数；默认 window。")
    intercept: bool = Field(default=True, description="回归是否包含截距。")

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesControlsRollingResidualParams":
        if self.min_periods is not None and self.min_periods > self.window:
            raise ValueError("params.min_periods 不能大于 params.window")
        return self


class TimeSeriesControlsRollingResidualOperator(TimeSeriesOperator):
    """每天重新拟合多元 OLS，只返回当天观测在当天窗口回归下的残差。"""

    op: Literal["controls.rolling_residual"] = Field(..., description="多元滚动 OLS 的当前观测残差。")
    fields: ControlsFields = Field(..., description="数值目标与有序的连续或 BOOL/STRING/SYMBOL 分类解释变量；共同排除缺失。")
    params: TimeSeriesControlsRollingResidualParams = Field(default_factory=TimeSeriesControlsRollingResidualParams)
    output_kind: ClassVar[OutputKind] = "NUMBER"
