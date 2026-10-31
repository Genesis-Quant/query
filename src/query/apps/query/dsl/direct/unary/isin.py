"""unary.isin 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import DirectOperator
from query.apps.query.dsl.fields import UnaryFields
from query.apps.query.dsl.types import (
    JsonScalar,
    OutputKind,
    StrictModel,
)


class DirectUnaryIsinParams(StrictModel):
    """unary.isin 参数。"""

    values: list[JsonScalar] = Field(..., min_length=1, description="允许匹配的常量集合。")


class DirectUnaryIsinOperator(DirectOperator):
    """判断是否属于常量集合。"""

    op: Literal['unary.isin'] = Field(..., description='判断是否属于常量集合。')
    fields: UnaryFields = Field(..., description="该算符严格定义的输入字段。")
    params: DirectUnaryIsinParams = Field(
        default_factory=DirectUnaryIsinParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'BOOL'
