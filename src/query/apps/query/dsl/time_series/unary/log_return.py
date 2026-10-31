"""unary.log_return 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryLogReturnParams(StrictModel):
    """unary.log_return 参数。"""

    periods: int = Field(default=1, ge=1, description="在 on=true 序列中的位移期数。")


class TimeSeriesUnaryLogReturnOperator(TimeSeriesOperator):
    """按股票执行 log_return。"""

    op: Literal['unary.log_return'] = Field(..., description='按股票执行 log_return。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryLogReturnParams = Field(
        default_factory=TimeSeriesUnaryLogReturnParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
