"""talib.ppo 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibPpoParams(StrictModel):
    """talib.ppo 参数。"""

    fast_period: int = Field(default=12, ge=2, description="快线周期。")
    slow_period: int = Field(default=26, ge=2, description="慢线周期。")
    ma_type: Literal[0, 1, 2, 3, 4, 5, 6, 8] = Field(
        default=0,
        description="TA-Lib 移动平均类型编号；当前 DolphinDB 不支持 MAMA(7)。",
    )

    @model_validator(mode="after")
    def validate_periods(self) -> "TimeSeriesTalibPpoParams":
        """要求快线周期小于慢线周期。"""
        if self.fast_period >= self.slow_period:
            raise ValueError("params.fast_period 必须小于 params.slow_period")
        return self


class TimeSeriesTalibPpoOperator(TimeSeriesOperator):
    """调用 ta::ppo。"""

    op: Literal['talib.ppo'] = Field(..., description='调用 ta::ppo。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibPpoParams = Field(
        default_factory=TimeSeriesTalibPpoParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
