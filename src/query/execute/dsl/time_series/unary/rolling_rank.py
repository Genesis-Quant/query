"""unary.rolling_rank 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
    Window,
)


class TimeSeriesUnaryRollingRankParams(StrictModel):
    """unary.rolling_rank 参数。"""

    window: Window = Field(..., description="整数为观测条数；字符串为日历窗口，如21d、12M、5y。")
    min_periods: int | None = Field(default=None, ge=1, description="产生结果所需的最少非空观测数。")
    ascending: bool = Field(default=True, description="是否按升序排名。")
    ties_method: Literal["min", "max", "average"] = Field(
        default="min", description="并列值处理方式。"
    )

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesUnaryRollingRankParams":
        """确保最少观测数不超过窗口。"""
        if isinstance(self.window, int) and self.min_periods is not None and self.min_periods > self.window:
            raise ValueError("params.min_periods 不能大于 params.window")
        return self


class TimeSeriesUnaryRollingRankOperator(TimeSeriesOperator):
    """按股票执行 rolling_rank。"""

    op: Literal['unary.rolling_rank'] = Field(..., description='按股票执行 rolling_rank。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryRollingRankParams = Field(
        default_factory=TimeSeriesUnaryRollingRankParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
