"""talib.plus_dm 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import HighLowFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibPlusDmParams(StrictModel):
    """talib.plus_dm 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibPlusDmOperator(TimeSeriesOperator):
    """调用 ta::plus_dm。"""

    op: Literal['talib.plus_dm'] = Field(..., description='调用 ta::plus_dm。')
    fields: HighLowFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibPlusDmParams = Field(
        default_factory=TimeSeriesTalibPlusDmParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
