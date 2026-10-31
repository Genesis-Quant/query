"""binary.beta 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionBinaryBetaParams(StrictModel):
    """binary.beta 不接收参数。"""


class CrossSectionBinaryBetaOperator(CrossSectionOperator):
    """按交易日执行 beta。"""

    op: Literal['binary.beta'] = Field(..., description='按交易日执行 beta。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionBinaryBetaParams = Field(
        default_factory=CrossSectionBinaryBetaParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
