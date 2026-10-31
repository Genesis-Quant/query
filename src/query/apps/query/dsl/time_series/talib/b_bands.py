"""talib.bBands 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import TimeSeriesOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class TimeSeriesTalibBBandsParams(StrictModel):
    """talib.bBands 参数。"""

    time_period: int = Field(..., ge=2, description="技术指标观察周期。")
    nbdev_up: float = Field(default=2.0, gt=0, allow_inf_nan=False, description="上轨标准差倍数。")
    nbdev_down: float = Field(default=2.0, gt=0, allow_inf_nan=False, description="下轨标准差倍数。")
    ma_type: Literal[0, 1, 2, 3, 4, 5, 6, 8] = Field(
        default=0,
        description="TA-Lib 移动平均类型编号；当前 DolphinDB 不支持 MAMA(7)。",
    )
    output: Literal["upper", "middle", "lower"] = Field(default="middle", description="需要返回的单个输出。")


class TimeSeriesTalibBBandsOperator(TimeSeriesOperator):
    """计算布林带并选择单个输出。"""

    op: Literal['talib.bBands'] = Field(..., description='计算布林带并选择单个输出。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: TimeSeriesTalibBBandsParams = Field(
        default_factory=TimeSeriesTalibBBandsParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
