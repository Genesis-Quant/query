"""grouped.demean 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import GroupedFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionGroupedDemeanParams(StrictModel):
    """grouped.demean 不接收参数。"""


class CrossSectionGroupedDemeanOperator(CrossSectionOperator):
    """按交易日和分类键执行 demean。"""

    op: Literal['grouped.demean'] = Field(..., description='按交易日和分类键执行 demean。')
    fields: GroupedFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionGroupedDemeanParams = Field(
        default_factory=CrossSectionGroupedDemeanParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
