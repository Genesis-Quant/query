"""talib.linearreg_slope 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibLinearregSlopeParams(StrictModel):
    """talib.linearreg_slope 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibLinearregSlopeOperator(TimeSeriesOperator):
    """调用 ta::linearreg_slope。"""

    op: Literal['talib.linearreg_slope'] = Field(..., description='调用 ta::linearreg_slope。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibLinearregSlopeParams = Field(
        default_factory=TimeSeriesTalibLinearregSlopeParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
