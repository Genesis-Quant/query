"""talib.aroon 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import HighLowFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibAroonParams(StrictModel):
    """talib.aroon 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")
    output: Literal["down", "up"] = Field(default="up", description="需要返回的单个输出。")


class TimeSeriesTalibAroonOperator(TimeSeriesOperator):
    """计算 Aroon 并选择单个输出。"""

    op: Literal['talib.aroon'] = Field(..., description='计算 Aroon 并选择单个输出。')
    fields: HighLowFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibAroonParams = Field(
        default_factory=TimeSeriesTalibAroonParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
