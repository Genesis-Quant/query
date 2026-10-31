"""talib.rocp 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibRocpParams(StrictModel):
    """talib.rocp 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibRocpOperator(TimeSeriesOperator):
    """调用 ta::rocp。"""

    op: Literal['talib.rocp'] = Field(..., description='调用 ta::rocp。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibRocpParams = Field(
        default_factory=TimeSeriesTalibRocpParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
