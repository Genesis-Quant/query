"""unary.zscore 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionUnaryZscoreParams(StrictModel):
    """unary.zscore 参数。"""

    ddof: Literal[0, 1] = Field(default=1, description="方差或标准差的自由度修正。")


class CrossSectionUnaryZscoreOperator(CrossSectionOperator):
    """按交易日执行 zscore。"""

    op: Literal['unary.zscore'] = Field(..., description='按交易日执行 zscore。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionUnaryZscoreParams = Field(
        default_factory=CrossSectionUnaryZscoreParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
