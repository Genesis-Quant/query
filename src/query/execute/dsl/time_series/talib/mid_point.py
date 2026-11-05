"""talib.midPoint 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibMidPointParams(StrictModel):
    """talib.midPoint 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibMidPointOperator(TimeSeriesOperator):
    """调用 ta::midPoint。"""

    op: Literal['talib.midPoint'] = Field(..., description='调用 ta::midPoint。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibMidPointParams = Field(
        default_factory=TimeSeriesTalibMidPointParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
