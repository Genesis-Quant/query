"""定义算符模型共用的严格 Schema 和类型。"""

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

JsonScalar = str | int | float | bool | None
OutputKind = Literal["BOOL", "NUMBER", "ANY"]


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
