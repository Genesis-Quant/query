"""binary.rolling_cov 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field, model_validator

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesBinaryRollingCovParams(StrictModel):
    """binary.rolling_cov 参数。"""

    window: int = Field(..., ge=1, description="on=true 序列中的窗口长度。")
    min_periods: int | None = Field(default=None, ge=1, description="产生结果所需的最少非空观测数。")

    @model_validator(mode="after")
    def validate_min_periods(self) -> "TimeSeriesBinaryRollingCovParams":
        """确保最少观测数不超过窗口。"""
        if self.min_periods is not None and self.min_periods > self.window:
            raise ValueError("params.min_periods 不能大于 params.window")
        return self


class TimeSeriesBinaryRollingCovOperator(TimeSeriesOperator):
    """按股票执行 rolling_cov。"""

    op: Literal['binary.rolling_cov'] = Field(..., description='按股票执行 rolling_cov。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesBinaryRollingCovParams = Field(
        default_factory=TimeSeriesBinaryRollingCovParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
