"""unary.cum_max 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryCumMaxParams(StrictModel):
    """unary.cum_max 参数。"""

    min_periods: int = Field(default=1, ge=1, description="产生结果所需的最少非空观测数。")


class TimeSeriesUnaryCumMaxOperator(TimeSeriesOperator):
    """按股票执行 cum_max。"""

    op: Literal['unary.cum_max'] = Field(..., description='按股票执行 cum_max。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryCumMaxParams = Field(
        default_factory=TimeSeriesUnaryCumMaxParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
