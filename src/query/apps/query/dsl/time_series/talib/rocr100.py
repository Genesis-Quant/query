"""talib.rocr100 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibRocr100Params(StrictModel):
    """talib.rocr100 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")


class TimeSeriesTalibRocr100Operator(TimeSeriesOperator):
    """调用 ta::rocr100。"""

    op: Literal['talib.rocr100'] = Field(..., description='调用 ta::rocr100。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibRocr100Params = Field(
        default_factory=TimeSeriesTalibRocr100Params,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
