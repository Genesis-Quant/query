"""talib.dema 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibDemaParams(StrictModel):
    """talib.dema 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibDemaOperator(TimeSeriesOperator):
    """调用 ta::dema。"""

    op: Literal['talib.dema'] = Field(..., description='调用 ta::dema。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibDemaParams = Field(
        default_factory=TimeSeriesTalibDemaParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
