"""talib.rsi 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibRsiParams(StrictModel):
    """talib.rsi 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibRsiOperator(TimeSeriesOperator):
    """调用 ta::rsi。"""

    op: Literal['talib.rsi'] = Field(..., description='调用 ta::rsi。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibRsiParams = Field(
        default_factory=TimeSeriesTalibRsiParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
