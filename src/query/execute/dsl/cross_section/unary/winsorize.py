"""unary.winsorize 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryWinsorizeParams(StrictModel):
    """unary.winsorize 参数。"""

    lower: float = Field(default=0.01, ge=0, lt=0.5, allow_inf_nan=False, description="下侧分位数。")
    upper: float = Field(default=0.99, gt=0.5, le=1, allow_inf_nan=False, description="上侧分位数。")

class CrossSectionUnaryWinsorizeOperator(CrossSectionOperator):
    """按交易日分位数缩尾。"""

    op: Literal['unary.winsorize'] = Field(..., description='按交易日分位数缩尾。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryWinsorizeParams = Field(
        default_factory=CrossSectionUnaryWinsorizeParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
