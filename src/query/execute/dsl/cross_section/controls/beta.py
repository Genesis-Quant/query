"""controls.beta 算符模型。"""

from typing import ClassVar, Literal

from pydantic import Field

from query.execute.dsl.base import CrossSectionOperator
from query.execute.dsl.fields import ControlsFields
from query.execute.dsl.types import OutputKind, StrictModel


class CrossSectionControlsBetaParams(StrictModel):
    """分类及连续变量截面回归的系数选择参数。"""

    intercept: bool = Field(default=True, description="正常回归是否包含截距。")
    index: int = Field(default=0, ge=0, description="0 起算的展开列索引，不包含截距；按原列顺序、类别升序去首类展开，索引不存在时返回 NULL。")


class CrossSectionControlsBetaOperator(CrossSectionOperator):
    """在共同有效行广播指定展开解释变量的系数，无效行返回 NULL。"""

    op: Literal["controls.beta"] = Field(..., description="多元截面 OLS 指定解释变量系数。")
    fields: ControlsFields = Field(..., description="数值目标与有序的连续或 BOOL/STRING/SYMBOL 分类解释变量。")
    params: CrossSectionControlsBetaParams = Field(default_factory=CrossSectionControlsBetaParams)
    output_kind: ClassVar[OutputKind] = "NUMBER"
