"""unary.rolling_any 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import BoolUnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
    Window,
)


class TimeSeriesUnaryRollingAnyParams(StrictModel):
    """unary.rolling_any 参数。"""

    window: Window = Field(..., description="整数为观测条数；字符串为日历窗口，如21d、12M、5y。")
    min_periods: int | None = Field(default=None, ge=1, description="产生结果所需的最少非空观测数。")

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesUnaryRollingAnyParams":
        """确保最少观测数不超过窗口。"""
        if isinstance(self.window, int) and self.min_periods is not None and self.min_periods > self.window:
            raise ValueError("params.min_periods 不能大于 params.window")
        return self


class TimeSeriesUnaryRollingAnyOperator(TimeSeriesOperator):
    """按股票执行 rolling_any。"""

    op: Literal['unary.rolling_any'] = Field(..., description='按股票执行 rolling_any。')
    fields: BoolUnaryFields = Field(..., description="该算符严格定义的 BOOL 输入字段。")
    params: TimeSeriesUnaryRollingAnyParams = Field(
        default_factory=TimeSeriesUnaryRollingAnyParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
