"""定义算符抽象基类及具体算符自动登记规则。"""

from typing import Any, Literal, get_args

from pydantic import BaseModel, Field

from .derivative import Derivative
from .fields import BoolOperand
from .types import StrictModel


class OperatorBase(Derivative):
    """所有具体算符模型的抽象基类。"""

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """校验具体算符类并按 op 自动登记。"""
        super().__pydantic_init_subclass__(**kwargs)
        if "op" not in cls.__dict__.get("__annotations__", {}):
            return

        values = get_args(cls.model_fields["op"].annotation)
        if len(values) != 1 or not isinstance(values[0], str):
            raise TypeError(f"{cls.__name__}.op 必须声明为单值 Literal")
        operation = values[0]
        if operation in cls.operators:
            other = cls.operators[operation]
            raise RuntimeError(
                f"算符 {operation!r} 重复定义："
                f"{other.__module__}.{other.__name__} 与 {cls.__module__}.{cls.__name__}"
            )

        fields_type = cls.model_fields["fields"].annotation
        params_type = cls.model_fields["params"].annotation
        if (
            fields_type is StrictModel
            or not isinstance(fields_type, type)
            or not issubclass(fields_type, BaseModel)
        ):
            raise RuntimeError(f"算符 {operation!r} 没有完整 fields BaseModel")
        if (
            params_type is StrictModel
            or not isinstance(params_type, type)
            or not issubclass(params_type, BaseModel)
        ):
            raise RuntimeError(f"算符 {operation!r} 没有完整 params BaseModel")
        if params_type.__bases__ != (StrictModel,):
            raise RuntimeError(
                f"算符 {operation!r} 的 params 必须在本文件中直接继承 StrictModel"
            )
        if params_type.__module__ != cls.__module__:
            raise RuntimeError(f"算符 {operation!r} 与其 params 必须位于同一文件")

        expected_params_name = cls.__name__.removesuffix("Operator") + "Params"
        if params_type.__name__ != expected_params_name:
            raise RuntimeError(
                f"算符 {operation!r} 的参数类应命名为 {expected_params_name}，"
                f"当前为 {params_type.__name__}"
            )

        type_values = get_args(cls.model_fields["type"].annotation)
        if len(type_values) != 1:
            raise RuntimeError(f"算符 {operation!r} 的 type 必须声明为单值 Literal")
        cls.operators[operation] = cls


class DirectOperator(OperatorBase):
    """不创建分组上下文且禁止 on 的直接计算算符。"""

    type: Literal["DIRECT"] = Field(..., description="直接计算类固定为 DIRECT。")


class TimeSeriesOperator(OperatorBase):
    """按 code 分组并按 time 排序的时序算符。"""

    type: Literal["TS"] = Field(..., description="时序计算类固定为 TS。")
    on: BoolOperand | None = Field(
        default=None,
        description=(
            "可选的 BOOL 列、BOOL 命名因子或返回 BOOL 的嵌套 DSL；"
            "None 表示不筛选，否则仅 true 行进入时序，false 和 NULL 行"
            "不参与且结果为 NULL。"
        ),
    )


class CrossSectionOperator(OperatorBase):
    """按 time 分组的截面算符。"""

    type: Literal["CS"] = Field(..., description="截面计算类固定为 CS。")
    on: BoolOperand | None = Field(
        default=None,
        description=(
            "可选的 BOOL 列、BOOL 命名因子或返回 BOOL 的嵌套 DSL；"
            "None 表示不筛选，否则仅 true 行进入截面，false 和 NULL 行"
            "不参与且结果为 NULL。"
        ),
    )
