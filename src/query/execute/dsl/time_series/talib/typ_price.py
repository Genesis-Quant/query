"""talib.typPrice 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import OHLCFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibTypPriceParams(StrictModel):
    """talib.typPrice 不接收参数。"""


class TimeSeriesTalibTypPriceOperator(TimeSeriesOperator):
    """调用 ta::typPrice。"""

    op: Literal['talib.typPrice'] = Field(..., description='调用 ta::typPrice。')
    fields: OHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibTypPriceParams = Field(
        default_factory=TimeSeriesTalibTypPriceParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
