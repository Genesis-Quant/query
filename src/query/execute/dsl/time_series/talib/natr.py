"""talib.natr 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import OHLCFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibNatrParams(StrictModel):
    """talib.natr 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期，底层 ATR/Wilder 要求至少 2。")


class TimeSeriesTalibNatrOperator(TimeSeriesOperator):
    """调用 ta::natr。"""

    op: Literal['talib.natr'] = Field(..., description='调用 ta::natr。')
    fields: OHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibNatrParams = Field(
        default_factory=TimeSeriesTalibNatrParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
