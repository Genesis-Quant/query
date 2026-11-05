"""talib.tema 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibTemaParams(StrictModel):
    """talib.tema 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibTemaOperator(TimeSeriesOperator):
    """调用 ta::tema。"""

    op: Literal['talib.tema'] = Field(..., description='调用 ta::tema。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibTemaParams = Field(
        default_factory=TimeSeriesTalibTemaParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
