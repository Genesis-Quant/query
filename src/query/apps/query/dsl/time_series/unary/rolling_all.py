"""unary.rolling_all 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import BoolUnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesUnaryRollingAllParams(StrictModel):
    """unary.rolling_all 参数。"""

    window: int = Field(..., ge=1, description="on=true 序列中的窗口长度。")
    min_periods: int | None = Field(default=None, ge=1, description="产生结果所需的最少非空观测数。")

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesUnaryRollingAllParams":
        """确保最少观测数不超过窗口。"""
        if self.min_periods is not None and self.min_periods > self.window:
            raise ValueError("params.min_periods 不能大于 params.window")
        return self


class TimeSeriesUnaryRollingAllOperator(TimeSeriesOperator):
    """按股票执行 rolling_all。"""

    op: Literal['unary.rolling_all'] = Field(..., description='按股票执行 rolling_all。')
    fields: BoolUnaryFields = Field(..., description="该算符严格定义的 BOOL 输入字段。")
    params: TimeSeriesUnaryRollingAllParams = Field(
        default_factory=TimeSeriesUnaryRollingAllParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
