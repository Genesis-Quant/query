"""binary.cov 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import BinaryFields
from query.execute.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionBinaryCovParams(StrictModel):
    """binary.cov 不接收参数。"""


class CrossSectionBinaryCovOperator(CrossSectionOperator):
    """按交易日执行 cov。"""

    op: Literal['binary.cov'] = Field(..., description='按交易日执行 cov。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionBinaryCovParams = Field(
        default_factory=CrossSectionBinaryCovParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
