"""定义算符模型共用的严格 Schema 和类型。"""

import math
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

JsonScalar = str | int | float | bool | None
OutputKind = Literal["BOOL", "NUMBER", "ANY"]
Window = Annotated[int, Field(ge=1)] | Annotated[
    str, Field(pattern=r"^[1-9][0-9]*(ms|s|m|h|H|d|w|M|y)$")
]
RegressionWeights = list[Annotated[float, Field(ge=0, allow_inf_nan=False)]]


def validate_regression_weights(window: Window, method: str, weights: RegressionWeights | None) -> None:
    """校验有限窗口权重；短窗口从权重末端对齐，不将缺失样本压缩后重新配权。"""
    if method == "ols":
        if weights is not None:
            raise ValueError("params.weights 仅用于 method=wls")
        return
    if weights is None or not weights or not any(weight > 0 for weight in weights):
        raise ValueError("method=wls 必须提供非空、非负且至少一项大于0的 params.weights")
    if isinstance(window, int) and len(weights) != window:
        raise ValueError("整数窗口的 params.weights 长度必须等于 params.window")


class StrictModel(BaseModel):
    """禁止额外字段、隐式类型转换和非有限浮点数。"""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_default=True,
        frozen=True,
    )

    @model_validator(mode="after")
    def reject_non_finite_numbers(self) -> "StrictModel":
        """递归拒绝 NaN 和正负无穷。"""

        def check(value: Any, path: str) -> None:
            """检查当前值及其嵌套子项是否包含非有限浮点数。"""
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"{path} 不能是 NaN 或正负无穷")
            if isinstance(value, BaseModel):
                for name, child in value.__dict__.items():
                    check(child, f"{path}.{name}")
            elif isinstance(value, (list, tuple)):
                for index, child in enumerate(value):
                    check(child, f"{path}[{index}]")

        for field_name, field_value in self.__dict__.items():
            check(field_value, field_name)
        return self


class RegressionFillRule(StrictModel):
    """回归单列缺失填充；常量必须显式给出且保持数值或分类类型。"""

    method: Literal["constant", "ffill", "mean"] = Field(
        default="ffill", description="constant 填指定常量，ffill 按股票前向填充，mean 填同日截面均值。"
    )
    value: JsonScalar = Field(default=None, description="仅 constant 使用的非 NULL、有限数值或非空分类常量；空字符串在 DolphinDB 中仍为缺失。")

    @model_validator(mode="after")
    def validate_value(self) -> "RegressionFillRule":
        if self.method == "constant":
            if self.value is None or self.value == "":
                raise ValueError("constant 填充必须指定非 NULL、非空字符串的 value")
        elif self.value is not None:
            raise ValueError("只有 constant 填充允许指定 value")
        return self


RegressionColumnFill = Literal["ffill", "mean"] | RegressionFillRule | None


class RegressionFill(StrictModel):
    """分别设置目标和有序控制列；省略的目标和控制列均默认 ffill。"""

    target: RegressionColumnFill = Field(
        default="ffill", description="目标填充规则；None 不填充，默认 ffill。"
    )
    controls: list[RegressionColumnFill] | None = Field(
        default=None,
        description="与 fields.controls 一一对应；列表项 None 不填充，省略或整体 None 表示所有控制默认 ffill。",
    )


RegressionFillMethod = RegressionColumnFill | RegressionFill
