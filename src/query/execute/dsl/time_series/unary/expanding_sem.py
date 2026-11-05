"""unary.expanding_sem 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryExpandingSemParams(StrictModel):
    """unary.expanding_sem 参数。"""

    min_periods: int = Field(default=1, ge=1, description="产生结果所需的最少非空观测数。")


class TimeSeriesUnaryExpandingSemOperator(TimeSeriesOperator):
    """按股票执行 expanding_sem。"""

    op: Literal['unary.expanding_sem'] = Field(..., description='按股票执行 expanding_sem。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryExpandingSemParams = Field(
        default_factory=TimeSeriesUnaryExpandingSemParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
