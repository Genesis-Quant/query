"""unary.cum_min 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryCumMinParams(StrictModel):
    """unary.cum_min 参数。"""

    min_periods: int = Field(default=1, ge=1, description="产生结果所需的最少非空观测数。")


class TimeSeriesUnaryCumMinOperator(TimeSeriesOperator):
    """按股票执行 cum_min。"""

    op: Literal['unary.cum_min'] = Field(..., description='按股票执行 cum_min。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryCumMinParams = Field(
        default_factory=TimeSeriesUnaryCumMinParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
