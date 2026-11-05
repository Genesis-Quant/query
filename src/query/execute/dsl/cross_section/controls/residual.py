"""controls.residual 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import ControlsFields
from query.execute.dsl.types import OutputKind, StrictModel


class CrossSectionControlsResidualParams(StrictModel):
    """分类及连续变量截面回归的残差参数。"""

    intercept: bool = Field(default=True, description="正常回归是否包含截距；小样本和无有效控制列返回去均值结果。")


class CrossSectionControlsResidualOperator(CrossSectionOperator):
    """连续或分类变量截面中性化，只返回残差，不附带去极值、标准化或补值。"""

    op: Literal["controls.residual"] = Field(..., description="多元截面 OLS 残差。")
    fields: ControlsFields = Field(..., description="数值目标与有序的连续或 BOOL/STRING/SYMBOL 分类解释变量。")
    params: CrossSectionControlsResidualParams = Field(default_factory=CrossSectionControlsResidualParams)
    output_kind: ClassVar[OutputKind] = "NUMBER"
