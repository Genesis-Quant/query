"""talib.var 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibVarParams(StrictModel):
    """talib.var 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")
    nbdev: float = Field(default=1.0, gt=0, allow_inf_nan=False, description="标准差倍数。")


class TimeSeriesTalibVarOperator(TimeSeriesOperator):
    """调用 ta::var。"""

    op: Literal['talib.var'] = Field(..., description='调用 ta::var。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibVarParams = Field(
        default_factory=TimeSeriesTalibVarParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
