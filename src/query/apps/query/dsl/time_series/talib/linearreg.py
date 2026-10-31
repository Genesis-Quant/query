"""talib.linearreg 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibLinearregParams(StrictModel):
    """talib.linearreg 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibLinearregOperator(TimeSeriesOperator):
    """调用 ta::linearreg。"""

    op: Literal['talib.linearreg'] = Field(..., description='调用 ta::linearreg。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibLinearregParams = Field(
        default_factory=TimeSeriesTalibLinearregParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
