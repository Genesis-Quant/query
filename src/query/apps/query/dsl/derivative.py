"""定义 DSL 入口模型及具体算符分发。"""

from typing import Any, ClassVar, Literal, Type

from pydantic import Field, model_validator

from .types import OutputKind, StrictModel


class Derivative(StrictModel):
    """根据 op 将 DSL 交给对应的具体算符模型校验。"""

    type: Literal["DIRECT", "TS", "CS"] = Field(..., description="算符计算类别。")
    op: str = Field(..., description="算符名称。")
    fields: StrictModel = Field(..., description="具体算符定义的字段模型。")
    params: StrictModel = Field(..., description="具体算符定义的参数模型。")

    operators: ClassVar[dict[str, Type["Derivative"]]] = {}
    output_kind: ClassVar[OutputKind] = "NUMBER"

    @model_validator(mode="wrap")
    @classmethod
    def dispatch_operator(cls, value: Any, handler: Any) -> "Derivative":
        """使用 op 对应的具体算符模型进行校验。"""
        if cls is not Derivative:
            return handler(value)
        if isinstance(value, Derivative):
            return value
        if not isinstance(value, dict):
            raise ValueError(
                f"Derivative 必须是 JSON 对象，当前类型为 {type(value).__name__}"
            )

        operation = value.get("op")
        if not isinstance(operation, str):
            raise ValueError("Derivative.op 为必填字符串")
        model = cls.operators.get(operation)
        if model is None:
            raise ValueError(f"不存在算符 {operation!r}")
        return model.model_validate(value)

    @model_validator(mode="after")
    def validate_on(self) -> "Derivative":
        """拒绝静态返回类型不是 BOOL 的嵌套 on。"""
        on = getattr(self, "on", None)
        if not isinstance(on, Derivative):
            return self
        if derivative_output_kind(on) != "BOOL":
            raise ValueError(
                f"{self.op} 的 on 嵌套表达式必须返回 BOOL，"
                f"当前 {on.op!r} 返回 {derivative_output_kind(on)}"
            )
        return self


def derivative_output_kind(derivative: Derivative) -> OutputKind:
    """返回派生节点的静态输出类型，并处理可确定类型的动态算符。"""
    if derivative.op == "unary.cast" and getattr(derivative.params, "dtype", None) == "bool":
        return "BOOL"
    if derivative.op == "nullary.literal" and (
            getattr(derivative.params, "dtype", None) == "bool"
            or isinstance(getattr(derivative.params, "value", None), bool)
    ):
        return "BOOL"
    return derivative.output_kind


def validate_bool_operand(value: Any, location: str) -> Any:
    """拒绝静态可确定为非 BOOL 的常量和嵌套派生节点。"""
    if isinstance(value, (str, bool)):
        return value
    if isinstance(value, Derivative) and derivative_output_kind(value) == "BOOL":
        return value
    if isinstance(value, Derivative):
        raise ValueError(f"{location} 必须返回 BOOL，当前 {value.op!r} 返回 {derivative_output_kind(value)}")
    raise ValueError(f"{location} 必须是 BOOL 常量、字段引用或返回 BOOL 的派生节点")
