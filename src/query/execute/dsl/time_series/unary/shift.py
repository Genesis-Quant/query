"""unary.shift 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryShiftParams(StrictModel):
    """unary.shift 参数。"""

    periods: int = Field(default=1, description="在 on=true 序列中的位移期数；负数表示读取未来观测。")


class TimeSeriesUnaryShiftOperator(TimeSeriesOperator):
    """按股票执行 shift。"""

    op: Literal['unary.shift'] = Field(..., description='按股票执行 shift。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryShiftParams = Field(
        default_factory=TimeSeriesUnaryShiftParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
