"""talib.midPrice 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import HighLowFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibMidPriceParams(StrictModel):
    """talib.midPrice 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibMidPriceOperator(TimeSeriesOperator):
    """调用 ta::midPrice。"""

    op: Literal['talib.midPrice'] = Field(..., description='调用 ta::midPrice。')
    fields: HighLowFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibMidPriceParams = Field(
        default_factory=TimeSeriesTalibMidPriceParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
