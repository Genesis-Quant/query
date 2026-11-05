"""binary.cross_below 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesBinaryCrossBelowParams(StrictModel):
    """binary.cross_below 不接收参数。"""


class TimeSeriesBinaryCrossBelowOperator(TimeSeriesOperator):
    """按股票判断 cross_below。"""

    op: Literal['binary.cross_below'] = Field(..., description='按股票判断 cross_below。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesBinaryCrossBelowParams = Field(
        default_factory=TimeSeriesBinaryCrossBelowParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
