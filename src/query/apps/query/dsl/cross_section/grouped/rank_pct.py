"""grouped.rank_pct 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import GroupedFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionGroupedRankPctParams(StrictModel):
    """grouped.rank_pct 参数。"""

    ascending: bool = Field(default=True, description="是否按升序排名。")
    ties_method: Literal["min", "max", "average", "first", "dense"] = Field(
        default="min", description="并列值处理方式。"
    )


class CrossSectionGroupedRankPctOperator(CrossSectionOperator):
    """按交易日和分类键执行 rank_pct。"""

    op: Literal['grouped.rank_pct'] = Field(..., description='按交易日和分类键执行 rank_pct。')
    fields: GroupedFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionGroupedRankPctParams = Field(
        default_factory=CrossSectionGroupedRankPctParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
