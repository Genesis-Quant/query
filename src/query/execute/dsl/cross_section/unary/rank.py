"""unary.rank 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryRankParams(StrictModel):
    """unary.rank 参数。"""

    ascending: bool = Field(default=True, description="是否按升序排名。")
    ties_method: Literal["min", "max", "average", "first", "dense"] = Field(
        default="min", description="并列值处理方式。"
    )


class CrossSectionUnaryRankOperator(CrossSectionOperator):
    """按交易日执行 rank。"""

    op: Literal['unary.rank'] = Field(..., description='按交易日执行 rank。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryRankParams = Field(
        default_factory=CrossSectionUnaryRankParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
