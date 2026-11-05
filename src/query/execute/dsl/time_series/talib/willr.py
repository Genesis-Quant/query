"""talib.willr 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import OHLCFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibWillrParams(StrictModel):
    """talib.willr 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibWillrOperator(TimeSeriesOperator):
    """调用 ta::willr。"""

    op: Literal['talib.willr'] = Field(..., description='调用 ta::willr。')
    fields: OHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibWillrParams = Field(
        default_factory=TimeSeriesTalibWillrParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
