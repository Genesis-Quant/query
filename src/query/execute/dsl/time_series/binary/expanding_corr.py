"""binary.expanding_corr 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesBinaryExpandingCorrParams(StrictModel):
    """binary.expanding_corr 参数。"""

    min_periods: int = Field(default=1, ge=1, description="产生结果所需的最少非空观测数。")


class TimeSeriesBinaryExpandingCorrOperator(TimeSeriesOperator):
    """按股票执行 expanding_corr。"""

    op: Literal['binary.expanding_corr'] = Field(..., description='按股票执行 expanding_corr。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesBinaryExpandingCorrParams = Field(
        default_factory=TimeSeriesBinaryExpandingCorrParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
