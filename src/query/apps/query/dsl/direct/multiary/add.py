"""multiary.add 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import MultiaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectMultiaryAddParams(StrictModel):
    """multiary.add 不接收参数。"""


class DirectMultiaryAddOperator(DirectOperator):
    """逐行多操作数 add 归约。"""

    op: Literal['multiary.add'] = Field(..., description='逐行多操作数 add 归约。')
    fields: MultiaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectMultiaryAddParams = Field(
        default_factory=DirectMultiaryAddParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
