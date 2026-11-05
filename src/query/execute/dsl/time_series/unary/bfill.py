"""unary.bfill 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryBfillParams(StrictModel):
    """unary.bfill 参数。"""

    limit: int | None = Field(default=None, ge=1, description="最多连续填充数量；NULL 表示不限。")


class TimeSeriesUnaryBfillOperator(TimeSeriesOperator):
    """按股票执行 bfill。"""

    op: Literal['unary.bfill'] = Field(..., description='按股票执行 bfill。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryBfillParams = Field(
        default_factory=TimeSeriesUnaryBfillParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'ANY'
