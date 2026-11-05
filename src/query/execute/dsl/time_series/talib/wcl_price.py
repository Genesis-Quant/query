"""talib.wclPrice 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import OHLCFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibWclPriceParams(StrictModel):
    """talib.wclPrice 不接收参数。"""


class TimeSeriesTalibWclPriceOperator(TimeSeriesOperator):
    """调用 ta::wclPrice。"""

    op: Literal['talib.wclPrice'] = Field(..., description='调用 ta::wclPrice。')
    fields: OHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibWclPriceParams = Field(
        default_factory=TimeSeriesTalibWclPriceParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
