"""talib.tsf 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibTsfParams(StrictModel):
    """talib.tsf 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")


class TimeSeriesTalibTsfOperator(TimeSeriesOperator):
    """调用 ta::tsf。"""

    op: Literal['talib.tsf'] = Field(..., description='调用 ta::tsf。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibTsfParams = Field(
        default_factory=TimeSeriesTalibTsfParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
