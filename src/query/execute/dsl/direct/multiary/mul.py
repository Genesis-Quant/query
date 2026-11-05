"""multiary.mul 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import MultiaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectMultiaryMulParams(StrictModel):
    """multiary.mul 不接收参数。"""


class DirectMultiaryMulOperator(DirectOperator):
    """逐行多操作数 mul 归约。"""

    op: Literal['multiary.mul'] = Field(..., description='逐行多操作数 mul 归约。')
    fields: MultiaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectMultiaryMulParams = Field(
        default_factory=DirectMultiaryMulParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
