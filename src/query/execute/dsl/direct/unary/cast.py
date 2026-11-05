"""unary.cast 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import DirectOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryCastParams(StrictModel):
    """unary.cast 参数。"""

    dtype: Literal[
        "bool", "int", "long", "float", "double", "string", "symbol", "date", "timestamp"
    ] = Field(..., description="目标 DolphinDB 数据类型。")


class DirectUnaryCastOperator(DirectOperator):
    """转换 DolphinDB 数据类型。"""

    op: Literal['unary.cast'] = Field(..., description='转换 DolphinDB 数据类型。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryCastParams = Field(
        default_factory=DirectUnaryCastParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'ANY'
