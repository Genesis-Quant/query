"""unary.acos 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class DirectUnaryAcosParams(StrictModel):
    """unary.acos 不接收参数。"""


class DirectUnaryAcosOperator(DirectOperator):
    """逐行执行 acos。"""

    op: Literal['unary.acos'] = Field(..., description='逐行执行 acos。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryAcosParams = Field(
        default_factory=DirectUnaryAcosParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
