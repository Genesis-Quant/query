"""talib.macd 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibMacdParams(StrictModel):
    """talib.macd 参数。"""

    fast_period: int = Field(default=12, ge=2, description="快线周期。")
    slow_period: int = Field(default=26, ge=2, description="慢线周期。")
    signal_period: int = Field(default=9, ge=1, description="信号线周期。")
    output: Literal["macd", "signal", "hist"] = Field(default="macd", description="需要返回的单个输出。")

    @model_validator(mode="after")
    def validate_periods(self) -> "TimeSeriesTalibMacdParams":
        """要求快线周期小于慢线周期。"""
        if self.fast_period >= self.slow_period:
            raise ValueError("params.fast_period 必须小于 params.slow_period")
        return self


class TimeSeriesTalibMacdOperator(TimeSeriesOperator):
    """计算 MACD 并选择单个输出。"""

    op: Literal['talib.macd'] = Field(..., description='计算 MACD 并选择单个输出。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibMacdParams = Field(
        default_factory=TimeSeriesTalibMacdParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
