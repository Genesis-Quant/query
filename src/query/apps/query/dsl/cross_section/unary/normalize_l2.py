"""unary.normalize_l2 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryNormalizeL2Params(StrictModel):
    """unary.normalize_l2 不接收参数。"""


class CrossSectionUnaryNormalizeL2Operator(CrossSectionOperator):
    """按交易日执行 normalize_l2。"""

    op: Literal['unary.normalize_l2'] = Field(..., description='按交易日执行 normalize_l2。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryNormalizeL2Params = Field(
        default_factory=CrossSectionUnaryNormalizeL2Params,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
