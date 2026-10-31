"""talib.ma 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibMaParams(StrictModel):
    """talib.ma 参数。"""

    time_period: int = Field(..., ge=1, description="技术指标观察周期。")
    ma_type: Literal[0, 1, 2, 3, 4, 5, 6, 8] = Field(
        default=0,
        description="TA-Lib 移动平均类型编号；当前 DolphinDB 不支持 MAMA(7)。",
    )


class TimeSeriesTalibMaOperator(TimeSeriesOperator):
    """调用 ta::ma。"""

    op: Literal['talib.ma'] = Field(..., description='调用 ta::ma。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibMaParams = Field(
        default_factory=TimeSeriesTalibMaParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
