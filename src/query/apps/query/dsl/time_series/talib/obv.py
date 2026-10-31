"""talib.obv 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import CloseVolumeFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibObvParams(StrictModel):
    """talib.obv 不接收参数。"""


class TimeSeriesTalibObvOperator(TimeSeriesOperator):
    """计算 OBV。"""

    op: Literal['talib.obv'] = Field(..., description='计算 OBV。')
    fields: CloseVolumeFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibObvParams = Field(
        default_factory=TimeSeriesTalibObvParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
