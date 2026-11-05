"""binary.expanding_cov 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import TimeSeriesOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesBinaryExpandingCovParams(StrictModel):
    """binary.expanding_cov 参数。"""

    min_periods: int = Field(default=1, ge=1, description="产生结果所需的最少非空观测数。")


class TimeSeriesBinaryExpandingCovOperator(TimeSeriesOperator):
    """按股票执行 expanding_cov。"""

    op: Literal['binary.expanding_cov'] = Field(..., description='按股票执行 expanding_cov。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesBinaryExpandingCovParams = Field(
        default_factory=TimeSeriesBinaryExpandingCovParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
