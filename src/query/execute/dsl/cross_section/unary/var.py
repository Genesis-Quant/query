"""unary.var 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import UnaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryVarParams(StrictModel):
    """unary.var 参数。"""

    ddof: Literal[0, 1] = Field(default=1, description="方差或标准差的自由度修正。")


class CrossSectionUnaryVarOperator(CrossSectionOperator):
    """按交易日广播 var 统计量。"""

    op: Literal['unary.var'] = Field(..., description='按交易日广播 var 统计量。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryVarParams = Field(
        default_factory=CrossSectionUnaryVarParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
