"""talib.cci 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import OHLCFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibCciParams(StrictModel):
    """talib.cci 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibCciOperator(TimeSeriesOperator):
    """调用 ta::cci。"""

    op: Literal['talib.cci'] = Field(..., description='调用 ta::cci。')
    fields: OHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibCciParams = Field(
        default_factory=TimeSeriesTalibCciParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
