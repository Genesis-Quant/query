"""talib.mom 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibMomParams(StrictModel):
    """talib.mom 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibMomOperator(TimeSeriesOperator):
    """调用 ta::mom。"""

    op: Literal['talib.mom'] = Field(..., description='调用 ta::mom。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibMomParams = Field(
        default_factory=TimeSeriesTalibMomParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
