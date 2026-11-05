"""unary.expanding_std 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryExpandingStdParams(StrictModel):
    """unary.expanding_std 参数。"""

    min_periods: int = Field(default=1, ge=1, description="产生结果所需的最少非空观测数。")


class TimeSeriesUnaryExpandingStdOperator(TimeSeriesOperator):
    """按股票执行 expanding_std。"""

    op: Literal['unary.expanding_std'] = Field(..., description='按股票执行 expanding_std。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryExpandingStdParams = Field(
        default_factory=TimeSeriesUnaryExpandingStdParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
