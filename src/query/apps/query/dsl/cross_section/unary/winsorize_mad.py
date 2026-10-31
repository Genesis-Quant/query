"""unary.winsorize_mad 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryWinsorizeMadParams(StrictModel):
    """unary.winsorize_mad 参数。"""

    n: float = Field(default=3.0, gt=0, allow_inf_nan=False, description="MAD 倍数。")
    scale: float = Field(default=1.4826, gt=0, allow_inf_nan=False, description="MAD 尺度系数。")


class CrossSectionUnaryWinsorizeMadOperator(CrossSectionOperator):
    """按交易日使用 MAD 缩尾。"""

    op: Literal['unary.winsorize_mad'] = Field(..., description='按交易日使用 MAD 缩尾。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryWinsorizeMadParams = Field(
        default_factory=CrossSectionUnaryWinsorizeMadParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
