"""talib.minus_di 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import OHLCFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibMinusDiParams(StrictModel):
    """talib.minus_di 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibMinusDiOperator(TimeSeriesOperator):
    """调用 ta::minus_di。"""

    op: Literal['talib.minus_di'] = Field(..., description='调用 ta::minus_di。')
    fields: OHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibMinusDiParams = Field(
        default_factory=TimeSeriesTalibMinusDiParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
