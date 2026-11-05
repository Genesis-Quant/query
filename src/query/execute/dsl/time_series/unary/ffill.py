"""unary.ffill 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryFfillParams(StrictModel):
    """unary.ffill 参数。"""

    limit: int | None = Field(default=None, ge=1, description="最多连续填充数量；NULL 表示不限。")


class TimeSeriesUnaryFfillOperator(TimeSeriesOperator):
    """按股票执行 ffill。"""

    op: Literal['unary.ffill'] = Field(..., description='按股票执行 ffill。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryFfillParams = Field(
        default_factory=TimeSeriesUnaryFfillParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'ANY'
