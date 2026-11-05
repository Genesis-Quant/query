"""talib.avgPrice 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import FullOHLCFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibAvgPriceParams(StrictModel):
    """talib.avgPrice 不接收参数。"""


class TimeSeriesTalibAvgPriceOperator(TimeSeriesOperator):
    """调用 ta::avgPrice。"""

    op: Literal['talib.avgPrice'] = Field(..., description='调用 ta::avgPrice。')
    fields: FullOHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibAvgPriceParams = Field(
        default_factory=TimeSeriesTalibAvgPriceParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
