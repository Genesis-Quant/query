"""unary.rank_pct 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryRankPctParams(StrictModel):
    """unary.rank_pct 参数。"""

    ascending: bool = Field(default=True, description="是否按升序排名。")
    ties_method: Literal["min", "max", "average", "first", "dense"] = Field(
        default="min", description="并列值处理方式。"
    )


class CrossSectionUnaryRankPctOperator(CrossSectionOperator):
    """按交易日执行 rank_pct。"""

    op: Literal['unary.rank_pct'] = Field(..., description='按交易日执行 rank_pct。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryRankPctParams = Field(
        default_factory=CrossSectionUnaryRankPctParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
