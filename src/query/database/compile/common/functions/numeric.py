"""数值算符共用的 DolphinDB 函数。"""

from query.database.compile import DolphinDBFunction

from .form import IS_SCALAR_FORM, IS_VECTOR_FORM

IS_FINITE_NUMBER = DolphinDBFunction(
    module="common",
    definition="""
    def is_finite_number(value) {
        // 逐元素判断有限数值，同时排除 NULL、NaN 和正负无穷。
        return isValid(value) && !isNanInf(double(value), true)
    }
    """
)

DIVIDE_OR_NULL = DolphinDBFunction(
    module="common",
    definition="""
    def divide_or_null(left, right) {
        // 执行安全除法；分母为 0 或 NULL 的位置返回 NULL。
        denominator = iif(isNull(right) || right == 0, double(NULL), double(right))
        return left / denominator
    }
    """
)

FLOOR_AS_DOUBLE = DolphinDBFunction(
    module="common",
    definition="""
    def floor_as_double(value) {
        // 以 DOUBLE 返回向下取整值，避免绝对值超过 LONG 范围时 floor 溢出为 NULL。
        threshold = 9007199254740992.0
        non_finite = isNanInf(double(value), false)
        return iif(non_finite || abs(value) >= threshold, double(value), double(floor(value)))
    }
    """
)

CAST_VALUE = DolphinDBFunction(
    module="common",
    definition="""
    def cast_value(value, dtype) {
        // 将标量或向量转换为 DSL 支持的目标类型，并显式解析日期时间字符串。
        if (dtype == "bool") return bool(value)
        if (dtype == "int") return int(value)
        if (dtype == "long") return long(value)
        if (dtype == "float") return float(value)
        if (dtype == "double") return double(value)
        if (dtype == "string") return string(value)
        if (dtype == "symbol") {
            text = string(value)
            if (is_scalar_form(text)) return symbol(enlist(text))
            return symbol(text)
        }
        if (dtype == "date") {
            if (type(value) == STRING) return temporalParse(value, "yyyy-MM-dd")
            return date(value)
        }
        if (dtype == "timestamp") {
            if (type(value) == STRING) {
                sample = value
                if (is_vector_form(value)) sample = value[0]
                if (size(split(sample, ".")) > 1) {
                    return timestamp(temporalParse(value, "yyyy-MM-ddTHH:mm:ss.SSS"))
                }
                return timestamp(temporalParse(value, "yyyy-MM-ddTHH:mm:ss"))
            }
            return timestamp(value)
        }
        throw "不支持转换为 dtype=" + string(dtype)
    }
    """,
    dependencies=(IS_SCALAR_FORM, IS_VECTOR_FORM),
)
