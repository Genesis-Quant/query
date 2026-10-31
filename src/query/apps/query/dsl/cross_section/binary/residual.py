"""binary.residual 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionBinaryResidualParams(StrictModel):
    """binary.residual 不接收参数。"""


class CrossSectionBinaryResidualOperator(CrossSectionOperator):
    """按交易日执行 residual。"""

    op: Literal['binary.residual'] = Field(..., description='按交易日执行 residual。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionBinaryResidualParams = Field(
        default_factory=CrossSectionBinaryResidualParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
