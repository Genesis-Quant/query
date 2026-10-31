"""grouped.zscore 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import GroupedFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionGroupedZscoreParams(StrictModel):
    """grouped.zscore 参数。"""

    ddof: Literal[0, 1] = Field(default=1, description="方差或标准差的自由度修正。")


class CrossSectionGroupedZscoreOperator(CrossSectionOperator):
    """按交易日和分类键执行 zscore。"""

    op: Literal['grouped.zscore'] = Field(..., description='按交易日和分类键执行 zscore。')
    fields: GroupedFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionGroupedZscoreParams = Field(
        default_factory=CrossSectionGroupedZscoreParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
