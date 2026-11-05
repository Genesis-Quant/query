"""multiary.min 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import MultiaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectMultiaryMinParams(StrictModel):
    """multiary.min 不接收参数。"""


class DirectMultiaryMinOperator(DirectOperator):
    """逐行多操作数 min 归约。"""

    op: Literal['multiary.min'] = Field(..., description='逐行多操作数 min 归约。')
    fields: MultiaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectMultiaryMinParams = Field(
        default_factory=DirectMultiaryMinParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
