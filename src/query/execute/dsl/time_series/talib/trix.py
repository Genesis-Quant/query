"""talib.trix 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibTrixParams(StrictModel):
    """talib.trix 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibTrixOperator(TimeSeriesOperator):
    """调用 ta::trix。"""

    op: Literal['talib.trix'] = Field(..., description='调用 ta::trix。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibTrixParams = Field(
        default_factory=TimeSeriesTalibTrixParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
