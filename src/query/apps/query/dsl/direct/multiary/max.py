"""multiary.max 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import MultiaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectMultiaryMaxParams(StrictModel):
    """multiary.max 不接收参数。"""


class DirectMultiaryMaxOperator(DirectOperator):
    """逐行多操作数 max 归约。"""

    op: Literal['multiary.max'] = Field(..., description='逐行多操作数 max 归约。')
    fields: MultiaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectMultiaryMaxParams = Field(
        default_factory=DirectMultiaryMaxParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
