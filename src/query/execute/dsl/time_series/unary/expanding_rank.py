"""unary.expanding_rank 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryExpandingRankParams(StrictModel):
    """unary.expanding_rank 参数。"""

    min_periods: int = Field(default=1, ge=1, description="产生结果所需的最少非空观测数。")
    ascending: bool = Field(default=True, description="是否按升序排名。")
    ties_method: Literal["min", "max", "average", "dense"] = Field(
        default="min", description="并列值处理方式。"
    )


class TimeSeriesUnaryExpandingRankOperator(TimeSeriesOperator):
    """按股票执行 expanding_rank。"""

    op: Literal['unary.expanding_rank'] = Field(..., description='按股票执行 expanding_rank。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryExpandingRankParams = Field(
        default_factory=TimeSeriesUnaryExpandingRankParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
