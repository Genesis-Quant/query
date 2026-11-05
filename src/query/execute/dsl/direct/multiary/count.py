"""multiary.count 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import MultiaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectMultiaryCountParams(StrictModel):
    """multiary.count 不接收参数。"""


class DirectMultiaryCountOperator(DirectOperator):
    """逐行多操作数 count 归约。"""

    op: Literal['multiary.count'] = Field(..., description='逐行多操作数 count 归约。')
    fields: MultiaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectMultiaryCountParams = Field(
        default_factory=DirectMultiaryCountParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
