"""binary.corr 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionBinaryCorrParams(StrictModel):
    """binary.corr 不接收参数。"""


class CrossSectionBinaryCorrOperator(CrossSectionOperator):
    """按交易日执行 corr。"""

    op: Literal['binary.corr'] = Field(..., description='按交易日执行 corr。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionBinaryCorrParams = Field(
        default_factory=CrossSectionBinaryCorrParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
