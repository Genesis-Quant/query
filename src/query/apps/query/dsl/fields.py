"""定义算符可复用的操作数字段模型。"""

from typing import Any, Union

from pydantic import Field, SerializeAsAny, field_validator

from .derivative import Derivative, validate_bool_operand
from .types import StrictModel

Operand = Union[str, int, float, bool, SerializeAsAny[Derivative]]
BoolOperand = Union[str, bool, SerializeAsAny[Derivative]]


class NullaryFields(StrictModel):
    """不接收操作数。"""


class UnaryFields(StrictModel):
    """包含一个操作数。"""

    col: Operand = Field(..., description="列名、命名因子、嵌套 DSL 或数值/布尔常量。")


class BinaryFields(StrictModel):
    """包含左右两个操作数。"""

    left: Operand = Field(
        ...,
        description="左侧列名、命名因子、嵌套 DSL 或数值/布尔常量。",
    )
    right: Operand = Field(
        ...,
        description="右侧列名、命名因子、嵌套 DSL 或数值/布尔常量。",
    )


class BoolUnaryFields(StrictModel):
    """包含一个必须为 BOOL 的操作数。"""

    col: BoolOperand = Field(..., description="BOOL 字段、常量或嵌套 DSL。")

    @field_validator("col")
    @classmethod
    def validate_col(cls, value: BoolOperand) -> BoolOperand:
        return validate_bool_operand(value, "fields.col")


class BoolBinaryFields(StrictModel):
    """包含两个必须为 BOOL 的操作数。"""

    left: BoolOperand = Field(..., description="左侧 BOOL 字段、常量或嵌套 DSL。")
    right: BoolOperand = Field(..., description="右侧 BOOL 字段、常量或嵌套 DSL。")

    @field_validator("left", "right")
    @classmethod
    def validate_operand(cls, value: BoolOperand, info: Any) -> BoolOperand:
        return validate_bool_operand(value, f"fields.{info.field_name}")


class TernaryFields(StrictModel):
    """包含条件、真值和假值三个操作数。"""

    condition: BoolOperand = Field(..., description="必须计算为 BOOL 的条件操作数。")
    if_true: Operand = Field(..., description="条件为 true 时返回的操作数。")
    if_false: Operand = Field(..., description="条件为 false 时返回的操作数。")

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, value: BoolOperand) -> BoolOperand:
        return validate_bool_operand(value, "fields.condition")


class MultiaryFields(StrictModel):
    """包含至少一个操作数。"""

    cols: list[Operand] = Field(..., min_length=1, description="参与逐行归约的操作数列表。")


class BoolMultiaryFields(StrictModel):
    """包含至少一个必须为 BOOL 的操作数。"""

    cols: list[BoolOperand] = Field(..., min_length=1, description="参与逻辑归约的 BOOL 操作数列表。")

    @field_validator("cols")
    @classmethod
    def validate_cols(cls, values: list[BoolOperand]) -> list[BoolOperand]:
        return [validate_bool_operand(value, f"fields.cols[{index}]") for index, value in enumerate(values)]


class GroupedFields(StrictModel):
    """包含待计算值和截面分类键。"""

    col: Operand = Field(..., description="待执行组内截面操作的值。")
    by: Operand = Field(..., description="BOOL、SYMBOL、STRING 或离散整数分类键。")


class ControlsFields(StrictModel):
    """包含回归目标和一个或多个控制变量。"""

    target: Operand = Field(..., description="回归因变量，必须为数值目标。")
    controls: list[Operand] = Field(..., min_length=1, description="有序的连续数值或 BOOL/STRING/SYMBOL 分类解释变量列表。")


class OHLCFields(StrictModel):
    """包含最高价、最低价和收盘价。"""

    high: Operand = Field(..., description="最高价。")
    low: Operand = Field(..., description="最低价。")
    close: Operand = Field(..., description="收盘价。")


class OHLCVFields(OHLCFields):
    """包含最高价、最低价、收盘价和成交量。"""

    volume: Operand = Field(..., description="成交量。")


class FullOHLCFields(StrictModel):
    """包含开盘价、最高价、最低价和收盘价。"""

    open: Operand = Field(..., description="开盘价。")
    high: Operand = Field(..., description="最高价。")
    low: Operand = Field(..., description="最低价。")
    close: Operand = Field(..., description="收盘价。")


class HighLowFields(StrictModel):
    """包含最高价和最低价。"""

    high: Operand = Field(..., description="最高价。")
    low: Operand = Field(..., description="最低价。")


class CloseVolumeFields(StrictModel):
    """包含收盘价和成交量。"""

    close: Operand = Field(..., description="收盘价。")
    volume: Operand = Field(..., description="成交量。")
