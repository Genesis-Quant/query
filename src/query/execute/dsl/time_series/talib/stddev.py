"""talib.stddev 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibStddevParams(StrictModel):
    """talib.stddev 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")
    nbdev: float = Field(default=1.0, gt=0, allow_inf_nan=False, description="标准差倍数。")


class TimeSeriesTalibStddevOperator(TimeSeriesOperator):
    """调用 ta::stddev。"""

    op: Literal['talib.stddev'] = Field(..., description='调用 ta::stddev。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibStddevParams = Field(
        default_factory=TimeSeriesTalibStddevParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
