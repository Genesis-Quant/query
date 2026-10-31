"""talib.t3 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibT3Params(StrictModel):
    """talib.t3 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")
    vfactor: float = Field(default=0.7, gt=0, le=1, allow_inf_nan=False, description="T3 成交量因子。")


class TimeSeriesTalibT3Operator(TimeSeriesOperator):
    """计算 T3 指标。"""

    op: Literal['talib.t3'] = Field(..., description='计算 T3 指标。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibT3Params = Field(
        default_factory=TimeSeriesTalibT3Params,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
