"""unary.rolling_rank_pct 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryRollingRankPctParams(StrictModel):
    """unary.rolling_rank_pct 参数。"""

    window: int = Field(..., ge=1, description="on=true 序列中的窗口长度。")
    min_periods: int | None = Field(default=None, ge=1, description="产生结果所需的最少非空观测数。")
    ascending: bool = Field(default=True, description="是否按升序排名。")
    ties_method: Literal["min", "max", "average"] = Field(
        default="min", description="并列值处理方式。"
    )

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesUnaryRollingRankPctParams":
        """确保最少观测数不超过窗口。"""
        if self.min_periods is not None and self.min_periods > self.window:
            raise ValueError("params.min_periods 不能大于 params.window")
        return self


class TimeSeriesUnaryRollingRankPctOperator(TimeSeriesOperator):
    """按股票执行 rolling_rank_pct。"""

    op: Literal['unary.rolling_rank_pct'] = Field(..., description='按股票执行 rolling_rank_pct。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryRollingRankPctParams = Field(
        default_factory=TimeSeriesUnaryRollingRankPctParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
