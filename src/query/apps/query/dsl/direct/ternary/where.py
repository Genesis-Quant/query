"""ternary.where 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import TernaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectTernaryWhereParams(StrictModel):
    """ternary.where 不接收参数。"""


class DirectTernaryWhereOperator(DirectOperator):
    """根据 BOOL 条件逐行选择值。"""

    op: Literal['ternary.where'] = Field(..., description='根据 BOOL 条件逐行选择值。')
    fields: TernaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectTernaryWhereParams = Field(
        default_factory=DirectTernaryWhereParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'ANY'
