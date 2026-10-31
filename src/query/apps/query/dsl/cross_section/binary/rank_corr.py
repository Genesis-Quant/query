"""binary.rank_corr 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import BinaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionBinaryRankCorrParams(StrictModel):
    """binary.rank_corr 不接收参数。"""


class CrossSectionBinaryRankCorrOperator(CrossSectionOperator):
    """按交易日执行 rank_corr。"""

    op: Literal['binary.rank_corr'] = Field(..., description='按交易日执行 rank_corr。')
    fields: BinaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionBinaryRankCorrParams = Field(
        default_factory=CrossSectionBinaryRankCorrParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
