"""talib.ad 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import OHLCVFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibAdParams(StrictModel):
    """talib.ad 不接收参数。"""


class TimeSeriesTalibAdOperator(TimeSeriesOperator):
    """计算 Chaikin A/D。"""

    op: Literal['talib.ad'] = Field(..., description='计算 Chaikin A/D。')
    fields: OHLCVFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibAdParams = Field(
        default_factory=TimeSeriesTalibAdParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
