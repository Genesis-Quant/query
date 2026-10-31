"""controls.alpha 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.apps.query.dsl.base import CrossSectionOperator
from query.apps.query.dsl.fields import ControlsFields
from query.apps.query.dsl.types import OutputKind, StrictModel


class CrossSectionControlsAlphaParams(StrictModel):
    """分类及连续变量截面回归的截距参数。"""

    intercept: bool = Field(default=True, description="正常回归是否含截距；退化样本沿用去均值规则。")


class CrossSectionControlsAlphaOperator(CrossSectionOperator):
    """按日期用分类和连续控制解释目标，在共同有效行广播截距，无效行返回 NULL。"""

    op: Literal["controls.alpha"] = Field(..., description="多元截面 OLS 截距。")
    fields: ControlsFields = Field(..., description="数值目标与有序的连续或 BOOL/STRING/SYMBOL 分类解释变量。")
    params: CrossSectionControlsAlphaParams = Field(default_factory=CrossSectionControlsAlphaParams)
    output_kind: ClassVar[OutputKind] = "NUMBER"
