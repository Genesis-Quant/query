"""unary.bottom_n 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryBottomNParams(StrictModel):
    """unary.bottom_n 参数。"""

    n: int = Field(..., ge=1, description="需要选择的股票数量。")


class CrossSectionUnaryBottomNOperator(CrossSectionOperator):
    """按交易日执行 bottom_n 选择。"""

    op: Literal['unary.bottom_n'] = Field(..., description='按交易日执行 bottom_n 选择。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryBottomNParams = Field(
        default_factory=CrossSectionUnaryBottomNParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
