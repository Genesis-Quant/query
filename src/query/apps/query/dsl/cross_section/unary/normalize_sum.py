"""unary.normalize_sum 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryNormalizeSumParams(StrictModel):
    """unary.normalize_sum 不接收参数。"""


class CrossSectionUnaryNormalizeSumOperator(CrossSectionOperator):
    """按交易日执行 normalize_sum。"""

    op: Literal['unary.normalize_sum'] = Field(..., description='按交易日执行 normalize_sum。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryNormalizeSumParams = Field(
        default_factory=CrossSectionUnaryNormalizeSumParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
