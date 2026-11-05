"""grouped.mean 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import GroupedFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionGroupedMeanParams(StrictModel):
    """grouped.mean 不接收参数。"""


class CrossSectionGroupedMeanOperator(CrossSectionOperator):
    """按交易日和分类键执行 mean。"""

    op: Literal['grouped.mean'] = Field(..., description='按交易日和分类键执行 mean。')
    fields: GroupedFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionGroupedMeanParams = Field(
        default_factory=CrossSectionGroupedMeanParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
