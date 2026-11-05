"""unary.decay_linear 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
    Window,
)


class TimeSeriesUnaryDecayLinearParams(StrictModel):
    """unary.decay_linear 参数。"""

    window: Window = Field(..., description="整数为观测条数；字符串为日历窗口。显式线性权重最多1024项。")
    min_periods: int | None = Field(default=None, ge=1, description="产生结果所需的最少非空观测数。")

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesUnaryDecayLinearParams":
        """确保最少观测数不超过窗口。"""
        if isinstance(self.window, int):
            if self.window > 1024:
                raise ValueError("params.window 不能大于 1024")
            if self.min_periods is not None and self.min_periods > self.window:
                raise ValueError("params.min_periods 不能大于 params.window")
        return self


class TimeSeriesUnaryDecayLinearOperator(TimeSeriesOperator):
    """按股票执行 decay_linear。"""

    op: Literal['unary.decay_linear'] = Field(..., description='按股票执行 decay_linear。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesUnaryDecayLinearParams = Field(
        default_factory=TimeSeriesUnaryDecayLinearParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
