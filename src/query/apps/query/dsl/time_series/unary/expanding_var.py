"""unary.expanding_var 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryExpandingVarParams(StrictModel):
    """unary.expanding_var 参数。"""

    min_periods: int = Field(default=1, ge=1, description="产生结果所需的最少非空观测数。")


class TimeSeriesUnaryExpandingVarOperator(TimeSeriesOperator):
    """按股票执行 expanding_var。"""

    op: Literal['unary.expanding_var'] = Field(..., description='按股票执行 expanding_var。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryExpandingVarParams = Field(
        default_factory=TimeSeriesUnaryExpandingVarParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
