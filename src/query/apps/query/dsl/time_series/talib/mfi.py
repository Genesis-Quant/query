"""talib.mfi 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import OHLCVFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibMfiParams(StrictModel):
    """talib.mfi 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibMfiOperator(TimeSeriesOperator):
    """计算资金流量指标。"""

    op: Literal['talib.mfi'] = Field(..., description='计算资金流量指标。')
    fields: OHLCVFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibMfiParams = Field(
        default_factory=TimeSeriesTalibMfiParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
