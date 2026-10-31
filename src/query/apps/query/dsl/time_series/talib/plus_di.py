"""talib.plus_di 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import OHLCFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibPlusDiParams(StrictModel):
    """talib.plus_di 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibPlusDiOperator(TimeSeriesOperator):
    """调用 ta::plus_di。"""

    op: Literal['talib.plus_di'] = Field(..., description='调用 ta::plus_di。')
    fields: OHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibPlusDiParams = Field(
        default_factory=TimeSeriesTalibPlusDiParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
