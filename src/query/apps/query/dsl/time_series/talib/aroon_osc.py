"""talib.aroonOsc 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import HighLowFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibAroonOscParams(StrictModel):
    """talib.aroonOsc 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibAroonOscOperator(TimeSeriesOperator):
    """调用 ta::aroonOsc。"""

    op: Literal['talib.aroonOsc'] = Field(..., description='调用 ta::aroonOsc。')
    fields: HighLowFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibAroonOscParams = Field(
        default_factory=TimeSeriesTalibAroonOscParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
