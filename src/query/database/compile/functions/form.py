"""数据形态判断共用的 DolphinDB 函数。"""

from .function import DolphinDBFunction

IS_SCALAR_FORM = DolphinDBFunction(
    module="common",
    definition="""
    def is_scalar_form(value) {
        // 判断 value 是否为标量；通过同形态对象比较，避免依赖 DolphinDB 内部 form 编号。
        return form(value) == form(0)
    }
    """
)

IS_VECTOR_FORM = DolphinDBFunction(
    module="common",
    definition="""
    def is_vector_form(value) {
        // 判断 value 是否为向量；不把矩阵、字典或表误判为一维操作数。
        return form(value) == form(0 1)
    }
    """
)

IS_DICTIONARY_FORM = DolphinDBFunction(
    module="common",
    definition="""
    def is_dictionary_form(value) {
        // 判断 value 是否为字典，供 JSON 定义和 DSL 节点的结构校验使用。
        return form(value) == form(dict(STRING, ANY))
    }
    """
)

IS_TABLE_FORM = DolphinDBFunction(
    module="common",
    definition="""
    def is_table_form(value) {
        // 判断 value 是否为表，供派生因子入口校验 source 使用。
        return form(value) == form(table(0 as value))
    }
    """
)

REQUIRE_TABLE_COLUMNS = DolphinDBFunction(
    module="common",
    definition="""
    def require_table_columns(source, names, location) {
        // 校验 source 为表、names 为 STRING 向量，并返回已经规范化的列名。
        if (!is_table_form(source)) {
            throw location + " 的 source 必须是 table，实际为 " + typestr(source)
        }
        if (!is_vector_form(names) || (size(names) > 0 && type(names) != STRING)) {
            throw location + " 的 names 必须是 STRING 向量，实际为 " + typestr(names)
        }
        normalized = string(names)
        missing = normalized[!(normalized in columnNames(source))]
        if (size(missing) > 0) {
            throw location + " 的列不存在：" + concat(missing, ", ")
        }
        return normalized
    }
    """,
    dependencies=(IS_TABLE_FORM, IS_VECTOR_FORM),
)
