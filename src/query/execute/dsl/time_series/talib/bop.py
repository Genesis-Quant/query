"""talib.bop 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import FullOHLCFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibBopParams(StrictModel):
    """talib.bop 不接收参数。"""


class TimeSeriesTalibBopOperator(TimeSeriesOperator):
    """调用 ta::bop。"""

    op: Literal['talib.bop'] = Field(..., description='调用 ta::bop。')
    fields: FullOHLCFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibBopParams = Field(
        default_factory=TimeSeriesTalibBopParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
