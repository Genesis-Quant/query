"""multiary.or 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import BoolMultiaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectMultiaryOrParams(StrictModel):
    """multiary.or 不接收参数。"""


class DirectMultiaryOrOperator(DirectOperator):
    """多条件逻辑 or。"""

    op: Literal['multiary.or'] = Field(..., description='多条件逻辑 or。')
    fields: BoolMultiaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectMultiaryOrParams = Field(
        default_factory=DirectMultiaryOrParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
