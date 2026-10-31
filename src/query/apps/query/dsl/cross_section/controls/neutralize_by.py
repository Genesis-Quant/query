"""controls.neutralize_by 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import ControlsFields
from query.apps.query.dsl.types import (
    OutputKind,
    StrictModel,
)


class CrossSectionControlsNeutralizeByParams(StrictModel):
    """controls.neutralize_by 参数。"""

    intercept: bool = Field(default=True, description="回归是否包含截距。")


class CrossSectionControlsNeutralizeByOperator(CrossSectionOperator):
    """按交易日执行分类和连续变量 OLS 中性化。"""

    op: Literal['controls.neutralize_by'] = Field(..., description='按交易日执行分类和连续变量 OLS 中性化。')
    fields: ControlsFields = Field(..., description="该算符严格定义的输入字段。")
    params: CrossSectionControlsNeutralizeByParams = Field(
        default_factory=CrossSectionControlsNeutralizeByParams,
        description="该算符严格定义的参数。",
    )
    output_kind: ClassVar[OutputKind] = 'NUMBER'
