"""unary.normalize_l1 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryNormalizeL1Params(StrictModel):
    """unary.normalize_l1 不接收参数。"""


class CrossSectionUnaryNormalizeL1Operator(CrossSectionOperator):
    """按交易日执行 normalize_l1。"""

    op: Literal['unary.normalize_l1'] = Field(..., description='按交易日执行 normalize_l1。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryNormalizeL1Params = Field(
        default_factory=CrossSectionUnaryNormalizeL1Params,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
