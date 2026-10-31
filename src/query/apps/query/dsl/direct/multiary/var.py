"""multiary.var 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import MultiaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectMultiaryVarParams(StrictModel):
    """multiary.var 参数。"""

    ddof: Literal[0, 1] = Field(default=1, description="方差或标准差的自由度修正。")


class DirectMultiaryVarOperator(DirectOperator):
    """逐行多操作数 var 归约。"""

    op: Literal['multiary.var'] = Field(..., description='逐行多操作数 var 归约。')
    fields: MultiaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectMultiaryVarParams = Field(
        default_factory=DirectMultiaryVarParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
