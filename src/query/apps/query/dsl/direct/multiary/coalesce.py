"""multiary.coalesce 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import MultiaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectMultiaryCoalesceParams(StrictModel):
    """multiary.coalesce 不接收参数。"""


class DirectMultiaryCoalesceOperator(DirectOperator):
    """逐行取第一个非空值。"""

    op: Literal['multiary.coalesce'] = Field(..., description='逐行取第一个非空值。')
    fields: MultiaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectMultiaryCoalesceParams = Field(
        default_factory=DirectMultiaryCoalesceParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'ANY'
