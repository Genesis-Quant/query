"""unary.rank_normal 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryRankNormalParams(StrictModel):
    """unary.rank_normal 参数。"""

    ascending: bool = Field(default=True, description="是否按升序排名。")


class CrossSectionUnaryRankNormalOperator(CrossSectionOperator):
    """按交易日执行 rank_normal。"""

    op: Literal['unary.rank_normal'] = Field(..., description='按交易日执行 rank_normal。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryRankNormalParams = Field(
        default_factory=CrossSectionUnaryRankNormalParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
