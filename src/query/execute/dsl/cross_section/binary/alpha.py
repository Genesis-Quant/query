"""binary.alpha 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionBinaryAlphaParams(StrictModel):
    """binary.alpha 不接收参数。"""


class CrossSectionBinaryAlphaOperator(CrossSectionOperator):
    """按交易日执行 alpha。"""

    op: Literal['binary.alpha'] = Field(..., description='按交易日执行 alpha。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionBinaryAlphaParams = Field(
        default_factory=CrossSectionBinaryAlphaParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
