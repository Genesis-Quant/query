"""talib.ultOsc 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import OHLCFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibUltOscParams(StrictModel):
    """talib.ultOsc 参数。"""

    period1: int = Field(default=7, ge=1, description="短周期。")
    period2: int = Field(default=14, ge=2, description="中周期。")
    period3: int = Field(default=28, ge=3, description="长周期。")

    @model_validator(mode="after")
    def validate_periods(self) -> "TimeSeriesTalibUltOscParams":
        """要求三个周期严格递增。"""
        if not self.period1 < self.period2 < self.period3:
            raise ValueError("params.period1/period2/period3 必须严格递增")
        return self


class TimeSeriesTalibUltOscOperator(TimeSeriesOperator):
    """计算终极振荡指标。"""

    op: Literal['talib.ultOsc'] = Field(..., description='计算终极振荡指标。')
    fields: OHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibUltOscParams = Field(
        default_factory=TimeSeriesTalibUltOscParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
