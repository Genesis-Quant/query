"""talib.beta 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import HighLowFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibBetaParams(StrictModel):
    """talib.beta 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibBetaOperator(TimeSeriesOperator):
    """调用 ta::beta。"""

    op: Literal['talib.beta'] = Field(..., description='调用 ta::beta。')
    fields: HighLowFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibBetaParams = Field(
        default_factory=TimeSeriesTalibBetaParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
