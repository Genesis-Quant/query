"""unary.bottom_pct 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryBottomPctParams(StrictModel):
    """unary.bottom_pct 参数。"""

    pct: float = Field(..., gt=0, le=1, allow_inf_nan=False, description="需要选择的截面比例。")


class CrossSectionUnaryBottomPctOperator(CrossSectionOperator):
    """按交易日执行 bottom_pct 选择。"""

    op: Literal['unary.bottom_pct'] = Field(..., description='按交易日执行 bottom_pct 选择。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryBottomPctParams = Field(
        default_factory=CrossSectionUnaryBottomPctParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
