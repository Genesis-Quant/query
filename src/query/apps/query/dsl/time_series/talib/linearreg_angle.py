"""talib.linearreg_angle 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibLinearregAngleParams(StrictModel):
    """talib.linearreg_angle 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibLinearregAngleOperator(TimeSeriesOperator):
    """调用 ta::linearreg_angle。"""

    op: Literal['talib.linearreg_angle'] = Field(..., description='调用 ta::linearreg_angle。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibLinearregAngleParams = Field(
        default_factory=TimeSeriesTalibLinearregAngleParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
