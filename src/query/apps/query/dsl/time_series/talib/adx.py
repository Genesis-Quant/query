"""talib.adx 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import OHLCFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibAdxParams(StrictModel):
    """talib.adx 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibAdxOperator(TimeSeriesOperator):
    """调用 ta::adx。"""

    op: Literal['talib.adx'] = Field(..., description='调用 ta::adx。')
    fields: OHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibAdxParams = Field(
        default_factory=TimeSeriesTalibAdxParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
