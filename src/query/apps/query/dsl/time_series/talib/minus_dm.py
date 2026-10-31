"""talib.minus_dm 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import HighLowFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibMinusDmParams(StrictModel):
    """talib.minus_dm 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibMinusDmOperator(TimeSeriesOperator):
    """调用 ta::minus_dm。"""

    op: Literal['talib.minus_dm'] = Field(..., description='调用 ta::minus_dm。')
    fields: HighLowFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibMinusDmParams = Field(
        default_factory=TimeSeriesTalibMinusDmParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
