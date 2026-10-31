"""unary.qcut 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryQcutParams(StrictModel):
    """unary.qcut 参数。"""

    q: int = Field(..., ge=2, description="分箱数量。")


class CrossSectionUnaryQcutOperator(CrossSectionOperator):
    """按交易日等频分箱。"""

    op: Literal['unary.qcut'] = Field(..., description='按交易日等频分箱。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryQcutParams = Field(
        default_factory=CrossSectionUnaryQcutParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
