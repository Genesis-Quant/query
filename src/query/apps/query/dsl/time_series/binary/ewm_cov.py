"""binary.ewm_cov 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesBinaryEwmCovParams(StrictModel):
    """binary.ewm_cov 参数。"""

    com: float | None = Field(default=None, ge=0, allow_inf_nan=False, description="质心衰减参数。")
    span: float | None = Field(default=None, ge=1, allow_inf_nan=False, description="跨度衰减参数。")
    half_life: float | None = Field(default=None, gt=0, allow_inf_nan=False, description="半衰期参数。")
    alpha: float | None = Field(default=None, gt=0, le=1, allow_inf_nan=False, description="平滑系数。")
    min_periods: int = Field(default=0, ge=0, description="产生结果所需的最少非空观测数。")
    adjust: bool = Field(default=True, description="是否使用完整权重归一化。")
    ignore_na: bool = Field(default=False, description="计算权重时是否忽略 NULL 位置。")
    bias: bool = Field(default=False, description="方差、标准差和协方差是否使用有偏估计。")

    @model_validator(mode="after")
    def validate_decay(self) -> "TimeSeriesBinaryEwmCovParams":
        """确保衰减参数恰好出现一个。"""
        values = [self.com, self.span, self.half_life, self.alpha]
        if sum(value is not None for value in values) != 1:
            raise ValueError("params.com/span/half_life/alpha 必须且只能提供一个")
        return self


class TimeSeriesBinaryEwmCovOperator(TimeSeriesOperator):
    """按股票执行 ewm_cov。"""

    op: Literal['binary.ewm_cov'] = Field(..., description='按股票执行 ewm_cov。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesBinaryEwmCovParams = Field(
        default_factory=TimeSeriesBinaryEwmCovParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
