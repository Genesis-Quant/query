"""talib.ema 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibEmaParams(StrictModel):
    """talib.ema 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibEmaOperator(TimeSeriesOperator):
    """调用 ta::ema。"""

    op: Literal['talib.ema'] = Field(..., description='调用 ta::ema。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibEmaParams = Field(
        default_factory=TimeSeriesTalibEmaParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
