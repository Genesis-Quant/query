"""talib.correl 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import HighLowFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibCorrelParams(StrictModel):
    """talib.correl 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibCorrelOperator(TimeSeriesOperator):
    """调用 ta::correl。"""

    op: Literal['talib.correl'] = Field(..., description='调用 ta::correl。')
    fields: HighLowFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibCorrelParams = Field(
        default_factory=TimeSeriesTalibCorrelParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
