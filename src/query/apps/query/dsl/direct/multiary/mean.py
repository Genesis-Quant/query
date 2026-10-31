"""multiary.mean 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import MultiaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectMultiaryMeanParams(StrictModel):
    """multiary.mean 不接收参数。"""


class DirectMultiaryMeanOperator(DirectOperator):
    """逐行多操作数 mean 归约。"""

    op: Literal['multiary.mean'] = Field(..., description='逐行多操作数 mean 归约。')
    fields: MultiaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectMultiaryMeanParams = Field(
        default_factory=DirectMultiaryMeanParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
