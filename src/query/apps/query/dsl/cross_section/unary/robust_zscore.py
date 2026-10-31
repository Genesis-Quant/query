"""unary.robust_zscore 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryRobustZscoreParams(StrictModel):
    """unary.robust_zscore 参数。"""

    scale: float = Field(default=1.4826, gt=0, allow_inf_nan=False, description="MAD 尺度系数。")


class CrossSectionUnaryRobustZscoreOperator(CrossSectionOperator):
    """按交易日执行稳健标准化。"""

    op: Literal['unary.robust_zscore'] = Field(..., description='按交易日执行稳健标准化。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryRobustZscoreParams = Field(
        default_factory=CrossSectionUnaryRobustZscoreParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
