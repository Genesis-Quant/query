"""talib.trange 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import OHLCFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibTrangeParams(StrictModel):
    """talib.trange 不接收参数。"""


class TimeSeriesTalibTrangeOperator(TimeSeriesOperator):
    """调用 ta::trange。"""

    op: Literal['talib.trange'] = Field(..., description='调用 ta::trange。')
    fields: OHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibTrangeParams = Field(
        default_factory=TimeSeriesTalibTrangeParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
