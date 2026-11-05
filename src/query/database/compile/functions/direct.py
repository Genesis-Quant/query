"""直接计算算符的 DolphinDB 函数。"""

from .function import DolphinDBFunction
from .numeric import (
    CAST_VALUE,
    DIVIDE_OR_NULL,
    FLOOR_AS_DOUBLE,
    IS_FINITE_NUMBER,
    REPLACE_VALUES,
    ROW_REDUCTION,
)

DIRECT_BINARY_ADD = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_add(left, right) {
        /*
        逐元素计算 left 与 right 的和。标量按 DolphinDB 广播规则参与运算。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            被加数；标量或与 right 等长的数值向量。
        right : scalar or vector
            加数；标量或与 left 等长的数值向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数在某位置为 NULL 时，该位置结果为 NULL；本算符不会跳过缺失值。

        广播与类型：标量可与向量逐元素广播，两个向量必须等长；结果 dtype 使用 DolphinDB
        的数值类型提升规则。

        Examples
        --------
        >>> left = 1.0 2.0 4.0
        >>> right = 3.0 2.0 1.0
        >>> direct_binary_add(left, right)
        [4, 4, 5]

        任一侧为 NULL 时传播缺失：
        >>> isNull(direct_binary_add(double([1, NULL]), double([2, 3])))
        [false, true]
        */
        return left + right
    }
    """
)

DIRECT_BINARY_AND = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_and(left, right) {
        /*
        逐元素计算 left 与 right 的逻辑与。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            左侧 BOOL 操作数。
        right : scalar or vector
            右侧 BOOL 操作数。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一侧为 BOOL NULL 时，该位置结果为 NULL；这里不使用 SQL 的三值短路化简，例如
        false && NULL 仍为 NULL。

        广播与类型：标量可与向量广播，输出保持输入广播后的形状且 dtype 为 BOOL。

        Examples
        --------
        >>> left = true true false false
        >>> right = true false true false
        >>> direct_binary_and(left, right)
        [true, false, false, false]

        BOOL NULL 传播到结果：
        >>> isNull(direct_binary_and(bool([true, NULL]), bool([false, true])))
        [false, true]
        */
        return left && right
    }
    """
)

DIRECT_BINARY_DAYS_BETWEEN = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_days_between(left, right) {
        /*
        逐元素计算 left 到 right 之间相差的自然日数。

        输入会先转换为 DATE，再按日历日计算 right - left；结果不包含时分秒差异。

        Parameters
        ----------
        left : scalar or vector
            起始日期或时间值。
        right : scalar or vector
            结束日期或时间值。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一日期为 NULL 时结果为 NULL。

        日期语义：两个输入先转换为 DATE，再计算自然日差；时间戳的时分秒部分会被截去，结果不使用交易日历。

        Examples
        --------
        >>> left = 2024.01.01 2024.02.28 2024.12.30
        >>> right = 2024.01.03 2024.03.01 2025.01.02
        >>> direct_binary_days_between(left, right)
        [-2, -2, -3]

        任一日期缺失时结果缺失：
        >>> isNull(direct_binary_days_between(date([2024.01.01, NULL]), date([2024.01.03, 2024.01.03])))
        [false, true]
        */
        return temporalDiff(date(left), date(right), "d")
    }
    """
)

DIRECT_BINARY_DIV = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_div(left, right) {
        /*
        逐元素计算 left 除以 right；除数为零的位置返回 NULL。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        right 为 0 或 NULL 的位置不执行运算，结果显式设为 NULL。

        Parameters
        ----------
        left : scalar or vector
            被除数；标量或数值向量。
        right : scalar or vector
            除数；0 和 NULL 会使对应结果为 NULL。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：left 或 right 为 NULL，以及 right 为 0 的位置都返回
        NULL。floor_div 和 mod 复用同一安全商，因此不会产生除零无穷值。

        广播与符号：标量可与向量广播。floor_div 对商向负无穷取整，mod 按 left -
        floor(left/right) * right 计算，负数结果遵循该定义。

        Examples
        --------
        >>> left = 5.0 8.0 11.0
        >>> right = 2.0 3.0 4.0
        >>> direct_binary_div(left, right)
        [2.5, 2.66667, 2.75]

        >>> left = 5.0 8.0 11.0
        >>> right = 2.0 0.0 4.0

        除数为零的位置返回 NULL：
        >>> direct_binary_div(left, right)
        [2.5, NULL, 2.75]
        */
        return divide_or_null(left, right)
    }
    """,
    dependencies=(DIVIDE_OR_NULL,)
)

DIRECT_BINARY_EQ = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_eq(left, right) {
        /*
        逐元素判断 left 是否等于 right。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            等值比较的左侧操作数。
        right : scalar or vector
            等值比较的右侧操作数。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数为 NULL 时结果为 BOOL NULL。需要判断缺失值时请显式使用
        unary.is_null 或 unary.not_null；该规则可防止未知比较结果被误作有效筛选条件。

        广播与类型：标量可与向量广播；跨 dtype 比较遵循 DolphinDB
        的公共类型转换规则，不做字符串形式的宽松比较。

        Examples
        --------
        >>> left = 1.0 2.0 4.0
        >>> right = 3.0 2.0 1.0
        >>> direct_binary_eq(left, right)
        [false, true, false]

        NULL 不参与等值判断：
        >>> direct_binary_eq(int([1, NULL, NULL]), int([1, 1, NULL]))
        [true, NULL, NULL]
        */
        return iif(isNull(left) || isNull(right), bool(NULL), left == right)
    }
    """
)

DIRECT_BINARY_FLOOR_DIV = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_floor_div(left, right) {
        /*
        逐元素执行向下取整除法；除数为零的位置返回 NULL。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        right 为 0 或 NULL 的位置不执行运算，结果显式设为 NULL。

        Parameters
        ----------
        left : scalar or vector
            向下整除的被除数。
        right : scalar or vector
            向下整除的除数；不能为 0。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：left 或 right 为 NULL，以及 right 为 0 的位置都返回
        NULL。floor_div 和 mod 复用同一安全商，因此不会产生除零无穷值。

        广播与符号：标量可与向量广播。floor_div 对商向负无穷取整，mod 按 left -
        floor(left/right) * right 计算，负数结果遵循该定义。

        Examples
        --------
        >>> left = 5.0 8.0 11.0
        >>> right = 2.0 3.0 4.0
        >>> direct_binary_floor_div(left, right)
        [2, 2, 2]

        >>> left = 5.0 8.0 11.0
        >>> right = 2.0 0.0 4.0

        除数为零的位置返回 NULL：
        >>> direct_binary_floor_div(left, right)
        [2, NULL, 2]
        */
        return floor_as_double(divide_or_null(left, right))
    }
    """,
    dependencies=(DIVIDE_OR_NULL, FLOOR_AS_DOUBLE)
)

DIRECT_BINARY_GE = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_ge(left, right) {
        /*
        逐元素判断 left 是否大于或等于 right。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            大于等于比较的左侧操作数。
        right : scalar or vector
            大于等于比较的右侧操作数。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数为 NULL 时结果为 BOOL NULL。需要判断缺失值时请显式使用
        unary.is_null 或 unary.not_null；该规则不会让 NULL 按 DolphinDB 排序最小值参与筛选。

        广播与类型：标量可与向量广播，两个向量必须等长；比较前的类型兼容性由 DolphinDB 判断。

        Examples
        --------
        >>> left = 1.0 2.0 4.0
        >>> right = 3.0 2.0 1.0
        >>> direct_binary_ge(left, right)
        [false, true, true]

        NULL 不参与有序比较：
        >>> direct_binary_ge(int([1, NULL, NULL]), int([0, 1, NULL]))
        [true, NULL, NULL]
        */
        return iif(isNull(left) || isNull(right), bool(NULL), left >= right)
    }
    """
)

DIRECT_BINARY_GT = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_gt(left, right) {
        /*
        逐元素判断 left 是否大于 right。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            大于比较的左侧操作数。
        right : scalar or vector
            大于比较的右侧操作数。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数为 NULL 时结果为 BOOL NULL。需要判断缺失值时请显式使用
        unary.is_null 或 unary.not_null；该规则不会让 NULL 按 DolphinDB 排序最小值参与筛选。

        广播与类型：标量可与向量广播，两个向量必须等长；比较前的类型兼容性由 DolphinDB 判断。

        Examples
        --------
        >>> left = 1.0 2.0 4.0
        >>> right = 3.0 2.0 1.0
        >>> direct_binary_gt(left, right)
        [false, false, true]

        NULL 不参与有序比较：
        >>> direct_binary_gt(int([1, NULL, NULL]), int([0, 1, NULL]))
        [true, NULL, NULL]
        */
        return iif(isNull(left) || isNull(right), bool(NULL), left > right)
    }
    """
)

DIRECT_BINARY_LE = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_le(left, right) {
        /*
        逐元素判断 left 是否小于或等于 right。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            小于等于比较的左侧操作数。
        right : scalar or vector
            小于等于比较的右侧操作数。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数为 NULL 时结果为 BOOL NULL。需要判断缺失值时请显式使用
        unary.is_null 或 unary.not_null；该规则不会让 NULL 按 DolphinDB 排序最小值参与筛选。

        广播与类型：标量可与向量广播，两个向量必须等长；比较前的类型兼容性由 DolphinDB 判断。

        Examples
        --------
        >>> left = 1.0 2.0 4.0
        >>> right = 3.0 2.0 1.0
        >>> direct_binary_le(left, right)
        [true, true, false]

        NULL 不参与有序比较：
        >>> direct_binary_le(int([1, NULL, NULL]), int([0, 1, NULL]))
        [false, NULL, NULL]
        */
        return iif(isNull(left) || isNull(right), bool(NULL), left <= right)
    }
    """
)

DIRECT_BINARY_LT = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_lt(left, right) {
        /*
        逐元素判断 left 是否小于 right。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            小于比较的左侧操作数。
        right : scalar or vector
            小于比较的右侧操作数。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数为 NULL 时结果为 BOOL NULL。需要判断缺失值时请显式使用
        unary.is_null 或 unary.not_null；该规则不会让 NULL 按 DolphinDB 排序最小值参与筛选。

        广播与类型：标量可与向量广播，两个向量必须等长；比较前的类型兼容性由 DolphinDB 判断。

        Examples
        --------
        >>> left = 1.0 2.0 4.0
        >>> right = 3.0 2.0 1.0
        >>> direct_binary_lt(left, right)
        [true, false, false]

        NULL 不参与有序比较：
        >>> direct_binary_lt(int([1, NULL, NULL]), int([0, 1, NULL]))
        [false, NULL, NULL]
        */
        return iif(isNull(left) || isNull(right), bool(NULL), left < right)
    }
    """
)

DIRECT_BINARY_MAXIMUM = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_maximum(left, right) {
        /*
        逐元素返回 left 与 right 中较大的值。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        任一操作数为 NULL 的位置返回 NULL。

        Parameters
        ----------
        left : scalar or vector
            逐元素最大值的第一个候选值。
        right : scalar or vector
            逐元素最大值的第二个候选值。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一侧为 NULL 时结果显式设为 NULL，不像行聚合算符那样跳过缺失值。

        平局与广播：两值相等时返回该值；标量可与向量广播，结果 dtype 使用两侧的公共类型。

        Examples
        --------
        >>> left = 1.0 2.0 4.0
        >>> right = 3.0 2.0 1.0
        >>> direct_binary_maximum(left, right)
        [3, 2, 4]

        二元极值不跳过 NULL：
        >>> isNull(direct_binary_maximum(double([1, NULL]), double([2, 3])))
        [false, true]
        */
        return iif(isNull(left) || isNull(right), NULL, iif(left >= right, left, right))
    }
    """
)

DIRECT_BINARY_MINIMUM = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_minimum(left, right) {
        /*
        逐元素返回 left 与 right 中较小的值。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        任一操作数为 NULL 的位置返回 NULL。

        Parameters
        ----------
        left : scalar or vector
            逐元素最小值的第一个候选值。
        right : scalar or vector
            逐元素最小值的第二个候选值。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一侧为 NULL 时结果显式设为 NULL，不像行聚合算符那样跳过缺失值。

        平局与广播：两值相等时返回该值；标量可与向量广播，结果 dtype 使用两侧的公共类型。

        Examples
        --------
        >>> left = 1.0 2.0 4.0
        >>> right = 3.0 2.0 1.0
        >>> direct_binary_minimum(left, right)
        [1, 2, 1]

        二元极值不跳过 NULL：
        >>> isNull(direct_binary_minimum(double([1, NULL]), double([2, 3])))
        [false, true]
        */
        return iif(isNull(left) || isNull(right), NULL, iif(left <= right, left, right))
    }
    """
)

DIRECT_BINARY_MOD = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_mod(left, right) {
        /*
        逐元素计算 left 除以 right 的余数；除数为零的位置返回 NULL。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        right 为 0 或 NULL 的位置不执行运算，结果显式设为 NULL。

        Parameters
        ----------
        left : scalar or vector
            取模运算的被除数。
        right : scalar or vector
            取模运算的除数；不能为 0。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：left 或 right 为 NULL，以及 right 为 0 的位置都返回
        NULL。floor_div 和 mod 复用同一安全商，因此不会产生除零无穷值。

        广播与符号：标量可与向量广播。floor_div 对商向负无穷取整，mod 按 left -
        floor(left/right) * right 计算，负数结果遵循该定义。

        Examples
        --------
        >>> left = 5.0 8.0 11.0
        >>> right = 2.0 3.0 4.0
        >>> direct_binary_mod(left, right)
        [1, 2, 3]

        >>> left = 5.0 8.0 11.0
        >>> right = 2.0 0.0 4.0

        除数为零的位置返回 NULL：
        >>> direct_binary_mod(left, right)
        [1, NULL, 3]
        */
        quotient = divide_or_null(left, right)
        return left - floor_as_double(quotient) * right
    }
    """,
    dependencies=(DIVIDE_OR_NULL, FLOOR_AS_DOUBLE)
)

DIRECT_BINARY_MUL = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_mul(left, right) {
        /*
        逐元素计算 left 与 right 的乘积。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            乘法的第一个因子。
        right : scalar or vector
            乘法的第二个因子。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数在某位置为 NULL 时，该位置结果为 NULL；本算符不会跳过缺失值。

        广播与类型：标量可与向量逐元素广播，两个向量必须等长；结果 dtype 使用 DolphinDB
        的数值类型提升规则。

        Examples
        --------
        >>> left = 1.0 2.0 4.0
        >>> right = 3.0 2.0 1.0
        >>> direct_binary_mul(left, right)
        [3, 4, 4]

        任一侧为 NULL 时传播缺失：
        >>> isNull(direct_binary_mul(double([1, NULL]), double([2, 3])))
        [false, true]
        */
        return left * right
    }
    """
)

DIRECT_BINARY_NE = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_ne(left, right) {
        /*
        逐元素判断 left 是否不等于 right。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            不等比较的左侧操作数。
        right : scalar or vector
            不等比较的右侧操作数。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数为 NULL 时结果为 BOOL NULL。需要判断缺失值时请显式使用
        unary.is_null 或 unary.not_null；该规则可防止未知比较结果被误作有效筛选条件。

        广播与类型：标量可与向量广播；跨 dtype 比较遵循 DolphinDB
        的公共类型转换规则，不做字符串形式的宽松比较。

        Examples
        --------
        >>> left = 1.0 2.0 4.0
        >>> right = 3.0 2.0 1.0
        >>> direct_binary_ne(left, right)
        [true, false, true]

        NULL 不参与不等判断：
        >>> direct_binary_ne(int([1, NULL, NULL]), int([1, 1, NULL]))
        [false, NULL, NULL]
        */
        return iif(isNull(left) || isNull(right), bool(NULL), left != right)
    }
    """
)

DIRECT_BINARY_NULL_IF = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_null_if(left, right) {
        /*
        逐元素比较两个操作数；相等时返回 NULL，否则返回 left。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        该算符常用于把特定哨兵值替换为 NULL；未匹配的位置保持 left 的原始类型和值。

        Parameters
        ----------
        left : scalar or vector
            需要保留或置空的源值。
        right : scalar or vector
            与 left 比较的值；相等时返回 NULL。

        Returns
        -------
        result : scalar or vector
            与广播后的 left 同形状和类型；匹配 right 的位置替换为 typed NULL。

        Notes
        -----
        NULL 处理：left 与 right 相等时返回 typed NULL；left 本身为 NULL 时结果也为
        NULL。NULL 与 NULL 按 DolphinDB 相等语义处理。

        广播与类型：输出类型跟随 left，right 仅用于比较；标量可与向量广播。

        Examples
        --------
        >>> left = 1 2 3 4
        >>> right = 0 2 0 4
        >>> direct_binary_null_if(left, right)
        [1, NULL, 3, NULL]

        相等值和缺失左值均返回 NULL：
        >>> direct_binary_null_if(double([1, NULL, 3]), double([1, 2, NULL]))
        [NULL, NULL, 3]
        */
        return iif(left == right, NULL, left)
    }
    """
)

DIRECT_BINARY_OR = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_or(left, right) {
        /*
        逐元素计算 left 与 right 的逻辑或。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            左侧 BOOL 操作数。
        right : scalar or vector
            右侧 BOOL 操作数。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一侧为 BOOL NULL 时，该位置结果为 NULL；这里不使用 SQL 的三值短路化简，例如
        false && NULL 仍为 NULL。

        广播与类型：标量可与向量广播，输出保持输入广播后的形状且 dtype 为 BOOL。

        Examples
        --------
        >>> left = true true false false
        >>> right = true false true false
        >>> direct_binary_or(left, right)
        [true, true, true, false]

        BOOL NULL 传播到结果：
        >>> isNull(direct_binary_or(bool([true, NULL]), bool([false, true])))
        [false, true]
        */
        return left || right
    }
    """
)

DIRECT_BINARY_POW = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_pow(left, right) {
        /*
        逐元素计算 left 的 right 次幂。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            幂运算的底数。
        right : scalar or vector
            幂运算的指数。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数在某位置为 NULL 时，该位置结果为
        NULL；本算符不会跳过缺失值。负底数配非整数指数等无实数结果的位置也会返回 NULL。

        广播与类型：标量可与向量逐元素广播，两个向量必须等长；结果 dtype 使用 DolphinDB
        的数值类型提升规则。

        Examples
        --------
        >>> left = 2.0 3.0 4.0
        >>> right = 2.0 3.0 0.5
        >>> direct_binary_pow(left, right)
        [4, 27, 2]

        任一侧为 NULL 时传播缺失：
        >>> isNull(direct_binary_pow(double([1, NULL]), double([2, 3])))
        [false, true]
        */
        return pow(left, right)
    }
    """
)

DIRECT_BINARY_SUB = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_sub(left, right) {
        /*
        逐元素计算 left 减去 right。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            减法的被减数。
        right : scalar or vector
            减法的减数。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数在某位置为 NULL 时，该位置结果为 NULL；本算符不会跳过缺失值。

        广播与类型：标量可与向量逐元素广播，两个向量必须等长；结果 dtype 使用 DolphinDB
        的数值类型提升规则。

        Examples
        --------
        >>> left = 1.0 2.0 4.0
        >>> right = 3.0 2.0 1.0
        >>> direct_binary_sub(left, right)
        [-2, 0, 3]

        任一侧为 NULL 时传播缺失：
        >>> isNull(direct_binary_sub(double([1, NULL]), double([2, 3])))
        [false, true]
        */
        return left - right
    }
    """
)

DIRECT_BINARY_XOR = DolphinDBFunction(
    module="query",
    definition="""
    def direct_binary_xor(left, right) {
        /*
        逐元素计算 left 与 right 的逻辑异或。

        当一侧为标量、另一侧为向量时，标量按元素广播；两个向量输入必须长度一致。

        Parameters
        ----------
        left : scalar or vector
            左侧 BOOL 操作数。
        right : scalar or vector
            右侧 BOOL 操作数。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一侧为 BOOL NULL 时，该位置结果为 NULL；这里不使用 SQL 的三值短路化简，例如
        false && NULL 仍为 NULL。

        广播与类型：标量可与向量广播，输出保持输入广播后的形状且 dtype 为 BOOL。

        Examples
        --------
        >>> left = true true false false
        >>> right = true false true false
        >>> direct_binary_xor(left, right)
        [false, true, true, false]

        BOOL NULL 传播到结果：
        >>> isNull(direct_binary_xor(bool([true, NULL]), bool([false, true])))
        [false, true]
        */
        return xor(left, right)
    }
    """
)

DIRECT_MULTIARY_ADD = DolphinDBFunction(
    module="query",
    definition="""
    def direct_multiary_add(cols) {
        /*
        按位置计算所有操作数的和。

        计算在每个位置独立进行。数值归约忽略 NULL；某位置没有有效操作数时返回 NULL。

        Parameters
        ----------
        cols : ANY vector
            按位置参与归约的操作数集合；其中的向量长度必须一致。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：逐行数值聚合忽略 NULL，只使用该行的有效输入；整行全部为 NULL 时返回 NULL。

        形状与类型：输入在执行前广播为等长向量，输出每行一个数值。该语义不同于普通二元算术算符的 NULL 传播。

        Examples
        --------
        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)
        >>> direct_multiary_add(cols)
        [11, 22, 33]

        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> first[1] = NULL
        >>> second[2] = NULL
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)

        NULL 不参与按行归约：
        >>> direct_multiary_add(cols)
        [11, 20, 3]
        */
        return row_reduction(cols, "add")
    }
    """,
    dependencies=(ROW_REDUCTION,),
)

DIRECT_MULTIARY_AND = DolphinDBFunction(
    module="query",
    definition="""
    def direct_multiary_and(cols) {
        /*
        按位置计算所有布尔操作数的逻辑与。

        计算在每个位置独立进行，并与依次嵌套 binary.and 的结果一致。

        Parameters
        ----------
        cols : ANY vector
            按位置参与归约的操作数集合；其中的向量长度必须一致。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数为 BOOL NULL 时，该位置结果为 NULL，与 binary.and
        使用相同的 NULL 传播规则。

        逻辑边界：按操作数顺序使用 && 归约。所有输入必须具有 BOOL
        语义并在广播后等长。

        Examples
        --------
        >>> first = true true false false
        >>> second = true false true false
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)
        >>> direct_multiary_and(cols)
        [true, false, false, false]

        任一条件为 NULL 时传播 NULL：
        >>> a = bool([true, false]); b = take(bool(NULL), 2)
        >>> direct_multiary_and([a, b])
        [NULL, NULL]
        */
        result = cols[0]
        if (size(cols) == 1) return result
        for (index in 1..(size(cols) - 1)) result = result && cols[index]
        return result
    }
    """
)

DIRECT_MULTIARY_COALESCE = DolphinDBFunction(
    module="query",
    definition="""
    def direct_multiary_coalesce(cols) {
        /*
        按位置返回第一个非 NULL 的操作数。

        cols 按给定顺序检查；一旦找到非 NULL 值便停止使用后续操作数。所有操作数均为 NULL 时返回 NULL。

        Parameters
        ----------
        cols : ANY vector
            按位置参与归约的操作数集合；其中的向量长度必须一致。

        Returns
        -------
        result : scalar or vector
            按优先级得到的公共类型结果；向量输入返回广播后的等长向量。

        Notes
        -----
        NULL 处理：按 cols 顺序返回每一行第一个非 NULL 值；该行所有输入均为 NULL 时结果为 NULL。

        顺序与类型：列顺序决定优先级，后续列只填补前面仍为空的位置；结果 dtype 由所有候选输入的公共类型决定。

        Examples
        --------
        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> first[1] = NULL
        >>> second[2] = NULL
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)
        >>> direct_multiary_coalesce(cols)
        [1, 20, 3]

        整行都缺失时保留 NULL：
        >>> direct_multiary_coalesce([double([1, NULL, NULL]), double([4, 5, NULL])])
        [1, 5, NULL]
        */
        result = cols[size(cols) - 1]
        if (size(cols) > 1) {
            for (index in (size(cols) - 2)..0) result = nullFill(cols[index], result)
        }
        return result
    }
    """
)

DIRECT_MULTIARY_COUNT = DolphinDBFunction(
    module="query",
    definition="""
    def direct_multiary_count(cols) {
        /*
        按位置统计非 NULL 操作数的数量。

        NULL 不计入数量；每个位置的结果范围为 0 到 size(cols)。

        Parameters
        ----------
        cols : ANY vector
            按位置参与归约的操作数集合；其中的向量长度必须一致。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：逐行只统计非 NULL 输入；全部为 NULL 的行返回 0。

        形状与类型：所有向量必须等长，标量由执行层广播后参与计算；输出为整数计数向量。

        Examples
        --------
        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> first[1] = NULL
        >>> second[2] = NULL
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)
        >>> direct_multiary_count(cols)
        [2, 1, 1]

        只统计非 NULL 输入：
        >>> direct_multiary_count([double([1, NULL, NULL]), double([4, 5, NULL])])
        [2, 1, 0]
        */
        return row_reduction(cols, "count")
    }
    """,
    dependencies=(ROW_REDUCTION,),
)

DIRECT_MULTIARY_MAX = DolphinDBFunction(
    module="query",
    definition="""
    def direct_multiary_max(cols) {
        /*
        按位置返回所有操作数中的最大值。

        计算在每个位置独立进行。数值归约忽略 NULL；某位置没有有效操作数时返回 NULL。

        Parameters
        ----------
        cols : ANY vector
            按位置参与归约的操作数集合；其中的向量长度必须一致。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：逐行数值聚合忽略 NULL，只使用该行的有效输入；整行全部为 NULL 时返回 NULL。

        形状与类型：输入在执行前广播为等长向量，输出每行一个数值。该语义不同于普通二元算术算符的 NULL 传播。

        Examples
        --------
        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)
        >>> direct_multiary_max(cols)
        [10, 20, 30]

        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> first[1] = NULL
        >>> second[2] = NULL
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)

        NULL 不参与按行归约：
        >>> direct_multiary_max(cols)
        [10, 20, 3]
        */
        return row_reduction(cols, "max")
    }
    """,
    dependencies=(ROW_REDUCTION,),
)

DIRECT_MULTIARY_MEAN = DolphinDBFunction(
    module="query",
    definition="""
    def direct_multiary_mean(cols) {
        /*
        按位置计算所有非 NULL 操作数的算术平均值。

        计算在每个位置独立进行。数值归约忽略 NULL；某位置没有有效操作数时返回 NULL。

        Parameters
        ----------
        cols : ANY vector
            按位置参与归约的操作数集合；其中的向量长度必须一致。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：逐行数值聚合忽略 NULL，只使用该行的有效输入；整行全部为 NULL 时返回 NULL。

        形状与类型：输入在执行前广播为等长向量，输出每行一个数值。该语义不同于普通二元算术算符的 NULL 传播。

        Examples
        --------
        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)
        >>> direct_multiary_mean(cols)
        [5.5, 11, 16.5]

        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> first[1] = NULL
        >>> second[2] = NULL
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)

        NULL 不参与按行归约：
        >>> direct_multiary_mean(cols)
        [5.5, 20, 3]
        */
        return row_reduction(cols, "mean")
    }
    """,
    dependencies=(ROW_REDUCTION,),
)

DIRECT_MULTIARY_MIN = DolphinDBFunction(
    module="query",
    definition="""
    def direct_multiary_min(cols) {
        /*
        按位置返回所有操作数中的最小值。

        计算在每个位置独立进行。数值归约忽略 NULL；某位置没有有效操作数时返回 NULL。

        Parameters
        ----------
        cols : ANY vector
            按位置参与归约的操作数集合；其中的向量长度必须一致。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：逐行数值聚合忽略 NULL，只使用该行的有效输入；整行全部为 NULL 时返回 NULL。

        形状与类型：输入在执行前广播为等长向量，输出每行一个数值。该语义不同于普通二元算术算符的 NULL 传播。

        Examples
        --------
        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)
        >>> direct_multiary_min(cols)
        [1, 2, 3]

        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> first[1] = NULL
        >>> second[2] = NULL
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)

        NULL 不参与按行归约：
        >>> direct_multiary_min(cols)
        [1, 20, 3]
        */
        return row_reduction(cols, "min")
    }
    """,
    dependencies=(ROW_REDUCTION,),
)

DIRECT_MULTIARY_MUL = DolphinDBFunction(
    module="query",
    definition="""
    def direct_multiary_mul(cols) {
        /*
        按位置计算所有操作数的乘积。

        计算在每个位置独立进行。数值归约忽略 NULL；某位置没有有效操作数时返回 NULL。

        Parameters
        ----------
        cols : ANY vector
            按位置参与归约的操作数集合；其中的向量长度必须一致。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：逐行数值聚合忽略 NULL，只使用该行的有效输入；整行全部为 NULL 时返回 NULL。

        形状与类型：输入在执行前广播为等长向量，输出每行一个数值。该语义不同于普通二元算术算符的 NULL 传播。

        Examples
        --------
        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)
        >>> direct_multiary_mul(cols)
        [10, 40, 90]

        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> first[1] = NULL
        >>> second[2] = NULL
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)

        NULL 不参与按行归约：
        >>> direct_multiary_mul(cols)
        [10, 20, 3]
        */
        return row_reduction(cols, "mul")
    }
    """,
    dependencies=(ROW_REDUCTION,),
)

DIRECT_MULTIARY_OR = DolphinDBFunction(
    module="query",
    definition="""
    def direct_multiary_or(cols) {
        /*
        按位置计算所有布尔操作数的逻辑或。

        计算在每个位置独立进行，并与依次嵌套 binary.or 的结果一致。

        Parameters
        ----------
        cols : ANY vector
            按位置参与归约的操作数集合；其中的向量长度必须一致。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：任一操作数为 BOOL NULL 时，该位置结果为 NULL，与 binary.or
        使用相同的 NULL 传播规则。

        逻辑边界：按操作数顺序使用 || 归约。所有输入必须具有 BOOL
        语义并在广播后等长。

        Examples
        --------
        >>> first = true true false false
        >>> second = true false true false
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)
        >>> direct_multiary_or(cols)
        [true, true, true, false]

        任一条件为 NULL 时传播 NULL：
        >>> a = bool([true, false]); b = take(bool(NULL), 2)
        >>> direct_multiary_or([a, b])
        [NULL, NULL]
        */
        result = cols[0]
        if (size(cols) == 1) return result
        for (index in 1..(size(cols) - 1)) result = result || cols[index]
        return result
    }
    """
)

DIRECT_MULTIARY_STD = DolphinDBFunction(
    module="query",
    definition="""
    def direct_multiary_std(cols, ddof) {
        /*
        按位置计算所有非 NULL 操作数的标准差。

        计算在每个位置独立进行，NULL 不参与该位置的统计。有效操作数不足以满足自由度时返回 NULL。

        Parameters
        ----------
        cols : ANY vector
            按位置参与归约的操作数集合；其中的向量长度必须一致。
        ddof : {0, 1}, default 1
            自由度修正。0 使用总体统计量，分母为 N；1 使用样本统计量，分母为 N - 1。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：逐行数值聚合忽略 NULL，只使用该行的有效输入；std/var 还要求有效值数量大于
        ddof，否则返回 NULL。

        形状与类型：输入在执行前广播为等长向量，输出每行一个数值。该语义不同于普通二元算术算符的 NULL 传播。

        Examples
        --------
        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)

        总体统计量，ddof=0：
        >>> direct_multiary_std(cols, 0)
        [4.5, 9, 13.5]

        样本统计量，ddof=1：
        >>> direct_multiary_std(cols, 1)
        [6.36396, 12.7279, 19.0919]
        */
        return row_reduction(cols, "std", int(ddof))
    }
    """,
    dependencies=(ROW_REDUCTION,),
)

DIRECT_MULTIARY_VAR = DolphinDBFunction(
    module="query",
    definition="""
    def direct_multiary_var(cols, ddof) {
        /*
        按位置计算所有非 NULL 操作数的方差。

        计算在每个位置独立进行，NULL 不参与该位置的统计。有效操作数不足以满足自由度时返回 NULL。

        Parameters
        ----------
        cols : ANY vector
            按位置参与归约的操作数集合；其中的向量长度必须一致。
        ddof : {0, 1}, default 1
            自由度修正。0 使用总体统计量，分母为 N；1 使用样本统计量，分母为 N - 1。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：逐行数值聚合忽略 NULL，只使用该行的有效输入；std/var 还要求有效值数量大于
        ddof，否则返回 NULL。

        形状与类型：输入在执行前广播为等长向量，输出每行一个数值。该语义不同于普通二元算术算符的 NULL 传播。

        Examples
        --------
        >>> first = 1.0 2.0 3.0
        >>> second = 10.0 20.0 30.0
        >>> cols = array(ANY, 0)
        >>> cols.append!(first)
        >>> cols.append!(second)

        总体统计量，ddof=0：
        >>> direct_multiary_var(cols, 0)
        [20.25, 81, 182.25]

        样本统计量，ddof=1：
        >>> direct_multiary_var(cols, 1)
        [40.5, 162, 364.5]
        */
        return row_reduction(cols, "var", int(ddof))
    }
    """,
    dependencies=(ROW_REDUCTION,),
)

DIRECT_NULLARY_FALSE = DolphinDBFunction(
    module="query",
    definition="""
    def direct_nullary_false() {
        /*
        返回布尔标量 false。

        Parameters
        ----------
        None
            此函数不接收参数。

        Returns
        -------
        result : BOOL
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：函数没有输入值，因此不会接收或传播 NULL；每次调用都返回非 NULL 的 BOOL 标量
        false。

        形状与用途：函数本身只返回标量。需要与向量配合时，由调用表达式显式广播，不能把它理解为已经具有输入表行数的布尔列。

        Examples
        --------
        >>> direct_nullary_false()
        false

        广播为三元素掩码：
        >>> take(direct_nullary_false(), 3)
        [false, false, false]
        */
        return false
    }
    """
)

DIRECT_NULLARY_LITERAL = DolphinDBFunction(
    module="query",
    definition="""
    def direct_nullary_literal(value, dtype) {
        /*
        把 JSON 标量转换为可选的 DolphinDB 类型并返回。

        dtype 为 NULL 时保留 value 的推断类型。NULL、DATE 和 TIMESTAMP 字面量必须显式给出
        dtype，日期时间字符串在进入函数前已由模型校验格式。

        Parameters
        ----------
        value : str or int or float or bool or NULL
            待转换的 JSON 标量。
        dtype : {"bool", "int", "long", "float", "double", "string", "symbol", "date", "timestamp"} or NULL, default NULL
            目标 DolphinDB 数据类型。DATE 和 TIMESTAMP 字符串必须分别符合 yyyy-MM-dd 和 ISO 日期时间格式。

        Returns
        -------
        result : Any
            一个推断类型或 dtype 指定类型的 DolphinDB 标量。

        Notes
        -----
        NULL 处理：value 为 NULL 时必须显式指定 dtype，结果是该 DolphinDB
        类型的空标量；dtype 为 NULL 只适用于可由 value 推断类型的非空字面量。

        类型与形状：该函数返回一个标量且不负责广播。数值转换可能发生精度收窄，DATE/TIMESTAMP 字符串格式在
        Python 模型构造阶段校验。

        Examples
        --------
        整数字面量：
        >>> direct_nullary_literal(42, "int")
        42

        双精度浮点字面量：
        >>> direct_nullary_literal(3.5, "double")
        3.5

        布尔字面量：
        >>> direct_nullary_literal(true, "bool")
        true

        字符串字面量：
        >>> direct_nullary_literal("bank", "string")
        "bank"

        SYMBOL 字面量：
        >>> direct_nullary_literal("bank", "symbol")
        "bank"

        DATE 字面量：
        >>> direct_nullary_literal("2024-01-02", "date")
        2024.01.02

        TIMESTAMP 字面量：
        >>> direct_nullary_literal("2024-01-02T09:30:00", "timestamp")
        2024.01.02T09:30:00

        显式类型的 NULL：
        >>> direct_nullary_literal(NULL, "double")
        NULL
        */
        if (isNull(dtype)) return value
        return cast_value(value, dtype)
    }
    """,
    dependencies=(CAST_VALUE,)
)

DIRECT_NULLARY_TRUE = DolphinDBFunction(
    module="query",
    definition="""
    def direct_nullary_true() {
        /*
        返回布尔标量 true。

        Parameters
        ----------
        None
            此函数不接收参数。

        Returns
        -------
        result : BOOL
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：函数没有输入值，因此不会接收或传播 NULL；每次调用都返回非 NULL 的 BOOL 标量
        true。

        形状与用途：函数本身只返回标量。需要与向量配合时，由调用表达式显式广播，不能把它理解为已经具有输入表行数的布尔列。

        Examples
        --------
        >>> direct_nullary_true()
        true

        广播为三元素掩码：
        >>> take(direct_nullary_true(), 3)
        [true, true, true]
        */
        return true
    }
    """
)

DIRECT_TERNARY_WHERE = DolphinDBFunction(
    module="query",
    definition="""
    def direct_ternary_where(condition, if_true, if_false) {
        /*
        根据 condition 逐元素选择 if_true 或 if_false。

        condition、if_true 和 if_false 按 DolphinDB 广播规则对齐；向量输入必须具有兼容长度。

        Parameters
        ----------
        condition : scalar or vector[BOOL]
            决定逐元素选择分支的布尔条件。
        if_true : scalar or vector
            条件为 true 时使用的值。
        if_false : scalar or vector
            条件为 false 时使用的值。

        Returns
        -------
        result : scalar or vector
            真值和假值分支的公共类型；形状由三个输入广播后确定。

        Notes
        -----
        NULL 处理：condition 为 NULL 时结果为 NULL；condition
        有效时只返回被选中分支的值，被选中分支为 NULL 则结果为 NULL。

        广播与类型：condition、if_true 和 if_false 可按 DolphinDB iif
        规则进行标量广播，两分支会转换到公共结果类型。

        Examples
        --------
        >>> condition = true false true false
        >>> if_true = 1 2 3 4
        >>> if_false = 10 20 30 40
        >>> direct_ternary_where(condition, if_true, if_false)
        [1, 20, 3, 40]

        >>> values = 1 2 3 4

        标量 true 选择完整真分支：
        >>> direct_ternary_where(true, values, 0)
        [1, 2, 3, 4]

        标量 false 选择完整假分支：
        >>> direct_ternary_where(false, values, 0)
        0
        */
        return iif(condition, if_true, if_false)
    }
    """
)

DIRECT_UNARY_ABS = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_abs(col) {
        /*
        逐元素返回输入值的绝对值。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：输入位置为 NULL 时，同位置结果为 NULL；本算符不做填充或缺失值替换。

        形状与类型：标量输入返回标量，向量输入保持长度并逐元素计算；数值类型按 DolphinDB
        对应内置函数的类型提升规则确定。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_abs(col)
        [2.5, 1, 0, 1.5, 3.2]

        NULL 保持在原位置：
        >>> isNull(direct_unary_abs(double([1, NULL])))
        [false, true]
        */
        return abs(col)
    }
    """
)

DIRECT_UNARY_ACOS = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_acos(col) {
        /*
        逐元素计算反余弦，输入值必须位于 [-1, 1]。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：有效定义域为 [-1, 1]；超出定义域的有限值与 NULL 都返回
        NULL。函数不会填充、删除或重排输入位置。

        形状与数值：标量输入返回标量，向量输入保持长度并逐元素计算。结果使用 DolphinDB
        浮点数学函数的精度和溢出规则。

        Examples
        --------
        >>> col = -1.0 -0.5 0.0 0.5 1.0
        >>> direct_unary_acos(col)
        [3.14159, 2.0944, 1.5708, 1.0472, 0]

        非法定义域和 NULL 都产生缺失结果：
        >>> isNull(direct_unary_acos(double([-2, NULL, 1])))
        [true, true, false]
        */
        return acos(col)
    }
    """
)

DIRECT_UNARY_ASIN = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_asin(col) {
        /*
        逐元素计算反正弦，输入值必须位于 [-1, 1]。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：有效定义域为 [-1, 1]；超出定义域的有限值与 NULL 都返回
        NULL。函数不会填充、删除或重排输入位置。

        形状与数值：标量输入返回标量，向量输入保持长度并逐元素计算。结果使用 DolphinDB
        浮点数学函数的精度和溢出规则。

        Examples
        --------
        >>> col = -1.0 -0.5 0.0 0.5 1.0
        >>> direct_unary_asin(col)
        [-1.5708, -0.523599, 0, 0.523599, 1.5708]

        非法定义域和 NULL 都产生缺失结果：
        >>> isNull(direct_unary_asin(double([-2, NULL, 1])))
        [true, true, false]
        */
        return asin(col)
    }
    """
)

DIRECT_UNARY_ATAN = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_atan(col) {
        /*
        逐元素计算反正切。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：输入位置为 NULL 时，同位置结果为 NULL；本算符不做填充或缺失值替换。

        形状与类型：标量输入返回标量，向量输入保持长度并逐元素计算；反正切结果以弧度返回，范围为 (-pi/2,
        pi/2)。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_atan(col)
        [-1.19029, -0.785398, 0, 0.982794, 1.26791]

        NULL 保持在原位置：
        >>> isNull(direct_unary_atan(double([1, NULL])))
        [false, true]
        */
        return atan(col)
    }
    """
)

DIRECT_UNARY_BETWEEN = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_between(col, lower, upper, inclusive) {
        /*
        逐元素判断输入值是否位于指定区间，并按 inclusive 控制边界。

        lower 必须不大于 upper。inclusive 分别控制左右端点是否使用闭区间比较。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。
        lower : float
            区间边界；lower 必须不大于 upper。
        upper : float
            区间边界；lower 必须不大于 upper。
        inclusive : {"both", "left", "right", "neither"}, default "both"
            边界包含方式：
            * "both"：包含 lower 和 upper。
            * "left"：只包含 lower。
            * "right"：只包含 upper。
            * "neither"：两个边界都不包含。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：col 为 NULL 时两个边界比较均不成立，结果为 false，而不是 NULL。

        边界行为：inclusive 分别控制左右端点使用闭区间还是开区间；lower 和 upper
        本身不参与自动排序，调用者必须提供正确顺序。

        Examples
        --------
        >>> col = 1 2 3 4 5

        inclusive="both"：
        >>> direct_unary_between(col, 2.0, 4.0, "both")
        [false, true, true, true, false]

        inclusive="left"：
        >>> direct_unary_between(col, 2.0, 4.0, "left")
        [false, true, true, false, false]

        inclusive="right"：
        >>> direct_unary_between(col, 2.0, 4.0, "right")
        [false, false, true, true, false]

        inclusive="neither"：
        >>> direct_unary_between(col, 2.0, 4.0, "neither")
        [false, false, true, false, false]
        */
        left_result = col > lower
        right_result = col < upper
        if (inclusive in ["both", "left"]) left_result = col >= lower
        if (inclusive in ["both", "right"]) right_result = col <= upper
        return left_result && right_result
    }
    """
)

DIRECT_UNARY_CAST = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_cast(col, dtype) {
        /*
        把输入值显式转换为指定的 DolphinDB 数据类型。

        转换失败时 DolphinDB 抛出类型错误。DATE 使用 yyyy-MM-dd 字符串，TIMESTAMP 使用 ISO 日期时间字符串。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。
        dtype : {"bool", "int", "long", "float", "double", "string", "symbol", "date", "timestamp"}
            目标 DolphinDB 数据类型。DATE 和 TIMESTAMP 字符串必须分别符合 yyyy-MM-dd 和 ISO 日期时间格式。

        Returns
        -------
        result : scalar or vector
            与 col 同形状、元素转换为 dtype 指定 DolphinDB 类型的结果。

        Notes
        -----
        NULL 处理：NULL 会转换为目标 dtype 的 typed NULL，不会被转换为 0、false
        或空字符串。

        转换边界：整数转换可能截断小数，窄类型转换可能损失精度；不支持的 dtype
        会抛出异常，DATE/TIMESTAMP 不负责时区转换。

        Examples
        --------
        >>> col = 1.2 2.8 3.5

        转换为布尔值，0 为 false，非 0 为 true：
        >>> direct_unary_cast(0 1 2, "bool")
        [false, true, true]

        转换为整数：
        >>> direct_unary_cast(col, "int")
        [1, 3, 4]

        转换为长整数：
        >>> direct_unary_cast(col, "long")
        [1, 3, 4]

        转换为单精度浮点数：
        >>> direct_unary_cast(col, "float")
        [1.2, 2.8, 3.5]

        转换为双精度浮点数：
        >>> direct_unary_cast(col, "double")
        [1.2, 2.8, 3.5]

        转换为字符串：
        >>> direct_unary_cast(col, "string")
        ["1.2", "2.8", "3.5"]

        转换字符串向量为 SYMBOL：
        >>> direct_unary_cast(["bank", "tech", "bank"], "symbol")
        ["bank", "tech", "bank"]

        >>> text = ["2024-01-02", "2024-12-31"]

        解析日期字符串：
        >>> direct_unary_cast(text, "date")
        [2024.01.02, 2024.12.31]

        解析时间戳字符串：
        >>> direct_unary_cast(["2024-01-02T09:30:00", "2024-01-02T15:00:00"], "timestamp")
        [2024.01.02T09:30:00, 2024.01.02T15:00:00]
        */
        return cast_value(col, dtype)
    }
    """,
    dependencies=(CAST_VALUE,)
)

DIRECT_UNARY_CEIL = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_ceil(col) {
        /*
        逐元素向正无穷方向取整。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：输入位置为 NULL 时，同位置结果为 NULL；本算符不做填充或缺失值替换。

        形状与类型：标量输入返回标量，向量输入保持长度并逐元素计算；结果按对应方向取整，但仍遵循 DolphinDB
        内置函数的返回 dtype。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_ceil(col)
        [-2, -1, 0, 2, 4]

        NULL 保持在原位置：
        >>> isNull(direct_unary_ceil(double([1, NULL])))
        [false, true]
        */
        return ceil(col)
    }
    """
)

DIRECT_UNARY_CLIP = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_clip(col, lower, upper) {
        /*
        把小于下界或大于上界的值分别截断到对应边界。

        lower 和 upper 至少提供一个；同时提供时 lower 必须不大于 upper。NULL 输入保持 NULL。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。
        lower : float or NULL, default NULL
            截断下界；NULL 表示不设置这一侧边界。lower 与 upper 至少提供一个。
        upper : float or NULL, default NULL
            截断上界；NULL 表示不设置这一侧边界。lower 与 upper 至少提供一个。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：col 为 NULL 的位置保持 NULL；边界不会用于填充缺失值。

        边界行为：小于 lower 的值替换为 lower，大于 upper 的值替换为
        upper，恰好等于边界的值保持不变。模型要求 lower 不大于 upper。

        Examples
        --------
        >>> col = 1 2 3 4 5

        同时设置上下界：
        >>> direct_unary_clip(col, 2.0, 4.0)
        [2, 2, 3, 4, 4]

        只设置下界：
        >>> direct_unary_clip(col, 2.0, double(NULL))
        [2, 2, 3, 4, 5]

        只设置上界：
        >>> direct_unary_clip(col, double(NULL), 4.0)
        [1, 2, 3, 4, 4]
        */
        result = col
        if (!isNull(lower)) {
            result = iif(isNull(result), result, iif(result < lower, lower, result))
        }
        if (!isNull(upper)) {
            result = iif(isNull(result), result, iif(result > upper, upper, result))
        }
        return result
    }
    """
)

DIRECT_UNARY_COS = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_cos(col) {
        /*
        逐元素计算余弦。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：输入位置为 NULL 时，同位置结果为 NULL；本算符不做填充或缺失值替换。

        形状与类型：标量输入返回标量，向量输入保持长度并逐元素计算；三角函数输入按弧度解释，不接受角度制标记。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_cos(col)
        [-0.801144, 0.540302, 1, 0.0707372, -0.998295]

        NULL 保持在原位置：
        >>> isNull(direct_unary_cos(double([1, NULL])))
        [false, true]
        */
        return cos(col)
    }
    """
)

DIRECT_UNARY_DAY = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_day(col) {
        /*
        从日期或时间值中提取月内日序号。

        Parameters
        ----------
        col : scalar or vector
            待提取的 DATE、TIMESTAMP 标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：时间值为 NULL 时，同位置结果为 NULL；布尔日期谓词也不会把缺失日期当作 false。

        输入约束：输入应为 DolphinDB temporal 类型。本算符不解析日期字符串，也不改变时区；结果采用对应
        DolphinDB 日历访问器的自然日定义，而不是交易日历。

        Examples
        --------
        >>> col = 2024.01.01 2024.02.29 2024.12.31
        >>> direct_unary_day(col)
        [1, 29, 31]

        缺失日期不会被解释为某个日历值：
        >>> isNull(direct_unary_day(date([2024.01.01, NULL])))
        [false, true]
        */
        return dayOfMonth(col)
    }
    """
)

DIRECT_UNARY_DAY_OF_YEAR = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_day_of_year(col) {
        /*
        从日期或时间值中提取年内日序号。

        Parameters
        ----------
        col : scalar or vector
            待提取的 DATE、TIMESTAMP 标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：时间值为 NULL 时，同位置结果为 NULL；布尔日期谓词也不会把缺失日期当作 false。

        输入约束：输入应为 DolphinDB temporal 类型。本算符不解析日期字符串，也不改变时区；结果采用对应
        DolphinDB 日历访问器的自然日定义，而不是交易日历。

        Examples
        --------
        >>> col = 2024.01.01 2024.02.29 2024.12.31
        >>> direct_unary_day_of_year(col)
        [1, 60, 366]

        缺失日期不会被解释为某个日历值：
        >>> isNull(direct_unary_day_of_year(date([2024.01.01, NULL])))
        [false, true]
        */
        return dayOfYear(col)
    }
    """
)

DIRECT_UNARY_EXP = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_exp(col) {
        /*
        逐元素计算自然指数函数。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：输入位置为 NULL 时，同位置结果为 NULL；本算符不做填充或缺失值替换。 exp/expm1
        的极大输入可能产生无穷值，本算符不会把无穷值自动改写为 NULL。

        形状与类型：标量输入返回标量，向量输入保持长度并逐元素计算；数值类型按 DolphinDB
        对应内置函数的类型提升规则确定。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_exp(col)
        [0.082085, 0.367879, 1, 4.48169, 24.5325]

        NULL 保持在原位置：
        >>> isNull(direct_unary_exp(double([1, NULL])))
        [false, true]
        */
        return exp(col)
    }
    """
)

DIRECT_UNARY_EXPM1 = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_expm1(col) {
        /*
        逐元素计算 exp(x) - 1，提高接近零时的数值精度。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：输入位置为 NULL 时，同位置结果为 NULL；本算符不做填充或缺失值替换。 exp/expm1
        的极大输入可能产生无穷值，本算符不会把无穷值自动改写为 NULL。

        形状与类型：标量输入返回标量，向量输入保持长度并逐元素计算；数值类型按 DolphinDB
        对应内置函数的类型提升规则确定。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_expm1(col)
        [-0.917915, -0.632121, 0, 3.48169, 23.5325]

        NULL 保持在原位置：
        >>> isNull(direct_unary_expm1(double([1, NULL])))
        [false, true]
        */
        return expm1(col)
    }
    """
)

DIRECT_UNARY_FLOOR = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_floor(col) {
        /*
        逐元素向负无穷方向取整。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：输入位置为 NULL 时，同位置结果为 NULL；本算符不做填充或缺失值替换。

        形状与类型：标量输入返回标量，向量输入保持长度并逐元素计算；结果按对应方向取整，但仍遵循 DolphinDB
        内置函数的返回 dtype。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_floor(col)
        [-3, -1, 0, 1, 3]

        NULL 保持在原位置：
        >>> isNull(direct_unary_floor(double([1, NULL])))
        [false, true]
        */
        return floor(col)
    }
    """
)

DIRECT_UNARY_GET = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_get(col) {
        /*
        原样返回已经求值的操作数。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector
            与 col 完全相同的类型、形状和值。

        Notes
        -----
        NULL 处理：输入按原值返回，NULL 的类型、位置和数量全部保持不变。

        形状与类型：这是恒等算符，不复制业务语义、不转换 dtype，也不对标量进行隐式广播。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_get(col)
        [-2.5, -1, 0, 1.5, 3.2]

        NULL 保持在原位置：
        >>> isNull(direct_unary_get(double([1, NULL])))
        [false, true]
        */
        return col
    }
    """
)

DIRECT_UNARY_ISIN = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_isin(col, values) {
        /*
        逐元素判断输入值是否属于给定常量集合。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。
        values : list[str or int or float or bool or NULL]
            用于成员判断的非空常量集合。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：DolphinDB 将同类型 NULL 视为可匹配值；values 包含 NULL 时，col 中的
        NULL 返回 true，否则返回 false。输出不包含 NULL。

        类型与形状：逐元素执行集合成员判断并返回同形状 BOOL，不做字符串或数值之间的隐式业务类型转换。

        Examples
        --------
        >>> col = 1 2 3 4 5
        >>> allowed = 2 4
        >>> direct_unary_isin(col, allowed)
        [false, true, false, true, false]

        >>> col = ["bank", "tech", "retail", "bank"]

        字符串集合匹配：
        >>> direct_unary_isin(col, ["bank", "retail"])
        [true, false, true, true]
        */
        return col in values
    }
    """
)

DIRECT_UNARY_IS_FINITE = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_is_finite(col) {
        /*
        逐元素判断数值是否既非 NULL 也非 NaN 或无穷。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：NULL、NaN、正无穷和负无穷都返回 false，普通有限数返回 true；输出自身不包含
        NULL。

        类型与形状：输出为 BOOL 且保持输入形状，适合在数值变换后显式过滤无效值。

        Examples
        --------
        >>> col = 1.0 2.0 3.0
        >>> col[1] = NULL
        >>> direct_unary_is_finite(col)
        [true, false, true]

        NULL 不是有限数：
        >>> direct_unary_is_finite(double([1, NULL]))
        [true, false]
        */
        return is_finite_number(col)
    }
    """,
    dependencies=(IS_FINITE_NUMBER,)
)

DIRECT_UNARY_IS_MONTH_END = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_is_month_end(col) {
        /*
        逐元素判断日期是否为月末。

        Parameters
        ----------
        col : scalar or vector
            待提取的 DATE、TIMESTAMP 标量或向量。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：时间值为 NULL 时，同位置结果为 NULL；布尔日期谓词也不会把缺失日期当作 false。

        输入约束：输入应为 DolphinDB temporal 类型。本算符不解析日期字符串，也不改变时区；结果采用对应
        DolphinDB 日历访问器的自然日定义，而不是交易日历。

        Examples
        --------
        >>> col = 2024.01.01 2024.02.29 2024.12.31
        >>> direct_unary_is_month_end(col)
        [false, true, true]

        缺失日期不会被解释为某个日历值：
        >>> isNull(direct_unary_is_month_end(date([2024.01.01, NULL])))
        [false, true]
        */
        return isMonthEnd(col)
    }
    """
)

DIRECT_UNARY_IS_NULL = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_is_null(col) {
        /*
        逐元素判断值是否为 NULL。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：NULL 返回 true，所有非 NULL 值返回 false；输出自身不包含 NULL。

        形状与类型：输出为与输入同形状的 BOOL，可直接用于 TS/CS 节点的 on 表达式。

        Examples
        --------
        >>> col = 1.0 2.0 3.0
        >>> col[1] = NULL
        >>> direct_unary_is_null(col)
        [false, true, false]

        识别缺失位置：
        >>> direct_unary_is_null(double([1, NULL]))
        [false, true]
        */
        return isNull(col)
    }
    """
)

DIRECT_UNARY_IS_QUARTER_END = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_is_quarter_end(col) {
        /*
        逐元素判断日期是否为季度末。

        Parameters
        ----------
        col : scalar or vector
            待提取的 DATE、TIMESTAMP 标量或向量。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：时间值为 NULL 时，同位置结果为 NULL；布尔日期谓词也不会把缺失日期当作 false。

        输入约束：输入应为 DolphinDB temporal 类型。本算符不解析日期字符串，也不改变时区；结果采用对应
        DolphinDB 日历访问器的自然日定义，而不是交易日历。

        Examples
        --------
        >>> col = 2024.01.01 2024.02.29 2024.12.31
        >>> direct_unary_is_quarter_end(col)
        [false, false, true]

        缺失日期不会被解释为某个日历值：
        >>> isNull(direct_unary_is_quarter_end(date([2024.01.01, NULL])))
        [false, true]
        */
        return isQuarterEnd(col)
    }
    """
)

DIRECT_UNARY_IS_WEEKEND = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_is_weekend(col) {
        /*
        逐元素判断日期是否为周六或周日。

        Parameters
        ----------
        col : scalar or vector
            待提取的 DATE、TIMESTAMP 标量或向量。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：时间值为 NULL 时，同位置结果为 NULL；布尔日期谓词也不会把缺失日期当作 false。

        输入约束：输入应为 DolphinDB temporal 类型。本算符不解析日期字符串，也不改变时区；结果采用对应
        DolphinDB 日历访问器的自然日定义，而不是交易日历。

        Examples
        --------
        >>> col = 2024.01.01 2024.02.29 2024.12.31
        >>> direct_unary_is_weekend(col)
        [false, false, false]

        缺失日期不会被解释为某个日历值：
        >>> isNull(direct_unary_is_weekend(date([2024.01.01, NULL])))
        [false, true]
        */
        return iif(isNull(col), bool(NULL), weekday(col, false) >= 5)
    }
    """
)

DIRECT_UNARY_IS_YEAR_END = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_is_year_end(col) {
        /*
        逐元素判断日期是否为年末。

        Parameters
        ----------
        col : scalar or vector
            待提取的 DATE、TIMESTAMP 标量或向量。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：时间值为 NULL 时，同位置结果为 NULL；布尔日期谓词也不会把缺失日期当作 false。

        输入约束：输入应为 DolphinDB temporal 类型。本算符不解析日期字符串，也不改变时区；结果采用对应
        DolphinDB 日历访问器的自然日定义，而不是交易日历。

        Examples
        --------
        >>> col = 2024.01.01 2024.02.29 2024.12.31
        >>> direct_unary_is_year_end(col)
        [false, false, true]

        缺失日期不会被解释为某个日历值：
        >>> isNull(direct_unary_is_year_end(date([2024.01.01, NULL])))
        [false, true]
        */
        return isYearEnd(col)
    }
    """
)

DIRECT_UNARY_LOG = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_log(col) {
        /*
        逐元素计算自然对数。

        输入必须为正数；不满足定义域的位置由 DolphinDB 返回 NULL。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：仅正数有定义；0、负数和 NULL 都返回 NULL。函数不会填充、删除或重排输入位置。

        形状与数值：标量输入返回标量，向量输入保持长度并逐元素计算。结果使用 DolphinDB
        浮点数学函数的精度和溢出规则。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 8.0
        >>> direct_unary_log(col)
        [0, 0.693147, 1.38629, 2.07944]

        非法定义域和 NULL 都产生缺失结果：
        >>> isNull(direct_unary_log(double([-1, NULL, 1])))
        [true, true, false]
        */
        return log(col)
    }
    """
)

DIRECT_UNARY_LOG10 = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_log10(col) {
        /*
        逐元素计算以 10 为底的对数。

        输入必须为正数；不满足定义域的位置由 DolphinDB 返回 NULL。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：仅正数有定义；0、负数和 NULL 都返回 NULL。函数不会填充、删除或重排输入位置。

        形状与数值：标量输入返回标量，向量输入保持长度并逐元素计算。结果使用 DolphinDB
        浮点数学函数的精度和溢出规则。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 8.0
        >>> direct_unary_log10(col)
        [0, 0.30103, 0.60206, 0.90309]

        非法定义域和 NULL 都产生缺失结果：
        >>> isNull(direct_unary_log10(double([-1, NULL, 1])))
        [true, true, false]
        */
        return log10(col)
    }
    """
)

DIRECT_UNARY_LOG1P = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_log1p(col) {
        /*
        逐元素计算 log(1 + x)，提高接近零时的数值精度。

        输入必须大于 -1；该实现比直接计算 log(1 + x) 更适合接近零的值。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：仅大于 -1 的值有定义；小于等于 -1 的值与 NULL 都返回
        NULL。函数不会填充、删除或重排输入位置。

        形状与数值：标量输入返回标量，向量输入保持长度并逐元素计算。结果使用 DolphinDB
        浮点数学函数的精度和溢出规则。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 8.0
        >>> direct_unary_log1p(col)
        [0.693147, 1.09861, 1.60944, 2.19722]

        非法定义域和 NULL 都产生缺失结果：
        >>> isNull(direct_unary_log1p(double([-2, NULL, 1])))
        [true, true, false]
        */
        return log1p(col)
    }
    """
)

DIRECT_UNARY_LOG2 = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_log2(col) {
        /*
        逐元素计算以 2 为底的对数。

        输入必须为正数；不满足定义域的位置由 DolphinDB 返回 NULL。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：仅正数有定义；0、负数和 NULL 都返回 NULL。函数不会填充、删除或重排输入位置。

        形状与数值：标量输入返回标量，向量输入保持长度并逐元素计算。结果使用 DolphinDB
        浮点数学函数的精度和溢出规则。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 8.0
        >>> direct_unary_log2(col)
        [0, 1, 2, 3]

        非法定义域和 NULL 都产生缺失结果：
        >>> isNull(direct_unary_log2(double([-1, NULL, 1])))
        [true, true, false]
        */
        return log2(col)
    }
    """
)

DIRECT_UNARY_MONTH = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_month(col) {
        /*
        从日期或时间值中提取月份。

        Parameters
        ----------
        col : scalar or vector
            待提取的 DATE、TIMESTAMP 标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：时间值为 NULL 时，同位置结果为 NULL；布尔日期谓词也不会把缺失日期当作 false。

        输入约束：输入应为 DolphinDB temporal 类型。本算符不解析日期字符串，也不改变时区；结果采用对应
        DolphinDB 日历访问器的自然日定义，而不是交易日历。

        Examples
        --------
        >>> col = 2024.01.01 2024.02.29 2024.12.31
        >>> direct_unary_month(col)
        [1, 2, 12]

        缺失日期不会被解释为某个日历值：
        >>> isNull(direct_unary_month(date([2024.01.01, NULL])))
        [false, true]
        */
        return monthOfYear(col)
    }
    """
)

DIRECT_UNARY_NEG = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_neg(col) {
        /*
        逐元素返回输入值的相反数。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：输入位置为 NULL 时，同位置结果为 NULL；本算符不做填充或缺失值替换。

        形状与类型：标量输入返回标量，向量输入保持长度并逐元素计算；数值类型按 DolphinDB
        对应内置函数的类型提升规则确定。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_neg(col)
        [2.5, 1, 0, -1.5, -3.2]

        NULL 保持在原位置：
        >>> isNull(direct_unary_neg(double([1, NULL])))
        [false, true]
        */
        return -col
    }
    """
)

DIRECT_UNARY_NOT = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_not(col) {
        /*
        逐元素计算逻辑非。

        Parameters
        ----------
        col : scalar or vector
            待取反的 BOOL 标量或向量。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：BOOL 输入为 NULL 时，逻辑取反结果仍为 NULL；不会把 NULL 当作 false。

        类型与形状：输入必须具有布尔语义，标量或向量形状保持不变。

        Examples
        --------
        >>> col = true false true false
        >>> direct_unary_not(col)
        [false, true, false, true]

        NULL 不会被当作 false：
        >>> direct_unary_not(bool([true, NULL, false]))
        [false, NULL, true]
        */
        return !col
    }
    """
)

DIRECT_UNARY_NOT_NULL = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_not_null(col) {
        /*
        逐元素判断值是否非 NULL。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[BOOL]
            布尔结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：NULL 返回 false，所有非 NULL 值返回 true；输出自身不包含 NULL。

        形状与类型：输出为与输入同形状的 BOOL，可直接用于 TS/CS 节点的 on 表达式。

        Examples
        --------
        >>> col = 1.0 2.0 3.0
        >>> col[1] = NULL
        >>> direct_unary_not_null(col)
        [true, false, true]

        识别有效位置：
        >>> direct_unary_not_null(double([1, NULL]))
        [true, false]
        */
        return !isNull(col)
    }
    """
)

DIRECT_UNARY_QUARTER = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_quarter(col) {
        /*
        从日期或时间值中提取季度序号。

        Parameters
        ----------
        col : scalar or vector
            待提取的 DATE、TIMESTAMP 标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：时间值为 NULL 时，同位置结果为 NULL；布尔日期谓词也不会把缺失日期当作 false。

        输入约束：输入应为 DolphinDB temporal 类型。本算符不解析日期字符串，也不改变时区；结果采用对应
        DolphinDB 日历访问器的自然日定义，而不是交易日历。

        Examples
        --------
        >>> col = 2024.01.01 2024.02.29 2024.12.31
        >>> direct_unary_quarter(col)
        [1, 1, 4]

        缺失日期不会被解释为某个日历值：
        >>> isNull(direct_unary_quarter(date([2024.01.01, NULL])))
        [false, true]
        */
        return quarterOfYear(col)
    }
    """
)

DIRECT_UNARY_REPLACE = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_replace(col, old, new) {
        /*
        按 old 与 new 的对应关系逐元素替换常量。

        old 与 new 必须非空且长度相同。替换按列表顺序依次执行，因此后一次替换可以继续匹配前一次产生的值。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。
        old : list[str or int or float or bool or NULL]
            待替换常量列表。 old 与 new 必须非空且长度相同。
        new : list[str or int or float or bool or NULL]
            替换后常量列表。 old 与 new 必须非空且长度相同。

        Returns
        -------
        result : scalar or vector
            与 col 同形状；dtype 由原值和 replacement 值的公共类型确定。

        Notes
        -----
        NULL 处理：未被 old 明确匹配的 NULL 保持为 NULL；替换按 old/new
        的对应顺序依次执行，后一次替换会看到前一次替换的结果。

        形状与类型：输出保持输入长度；old 不按输入类型窄化。数值结果按输入与 new 的最宽类型提升，
        文本和数值之间没有无损公共类型时明确报错，不静默转成 NULL。

        Examples
        --------
        >>> col = 1 2 3 4 5
        >>> old = 1 3
        >>> new = 10 30
        >>> direct_unary_replace(col, old, new)
        [10, 2, 30, 4, 5]

        >>> col = ["bank", "tech", "bank", "retail"]

        替换字符串值：
        >>> direct_unary_replace(col, ["bank", "tech"], ["finance", "growth"])
        ["finance", "growth", "finance", "retail"]

        >>> col = 1.0 2.0 3.0
        >>> col[1] = NULL

        替换 NULL：
        >>> direct_unary_replace(col, double(NULL), 0.0)
        [1, 0, 3]
        */
        return replace_values(col, old, new)
    }
    """,
    dependencies=(REPLACE_VALUES,),
)

DIRECT_UNARY_ROUND = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_round(col, precision) {
        /*
        逐元素按指定小数位数四舍五入。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。
        precision : int, default 0
            保留的小数位数；0 表示取整。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：NULL 位置保持 NULL。

        数值边界：digits 控制小数位数并使用 DolphinDB round
        的舍入规则；舍入改变数值而不改变向量长度，浮点表示仍可能包含机器精度误差。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2

        保留 0 位小数：
        >>> direct_unary_round(col, 0)
        [-3, -1, 0, 2, 3]

        保留 1 位小数：
        >>> direct_unary_round(col, 1)
        [-2.5, -1, 0, 1.5, 3.2]

        保留 2 位小数：
        >>> direct_unary_round(col, 2)
        [-2.5, -1, 0, 1.5, 3.2]
        */
        return round(col, int(precision))
    }
    """
)

DIRECT_UNARY_SIGN = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_sign(col) {
        /*
        逐元素返回负数、零和正数对应的 -1、0 和 1。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：输入位置为 NULL 时，同位置结果为 NULL；本算符不做填充或缺失值替换。

        形状与类型：标量输入返回标量，向量输入保持长度并逐元素计算；有效输入分别映射为 -1、0 或 1。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_sign(col)
        [-1, -1, 0, 1, 1]

        NULL 保持在原位置：
        >>> isNull(direct_unary_sign(double([1, NULL])))
        [false, true]
        */
        return signum(col)
    }
    """
)

DIRECT_UNARY_SIN = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_sin(col) {
        /*
        逐元素计算正弦。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：输入位置为 NULL 时，同位置结果为 NULL；本算符不做填充或缺失值替换。

        形状与类型：标量输入返回标量，向量输入保持长度并逐元素计算；三角函数输入按弧度解释，不接受角度制标记。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_sin(col)
        [-0.598472, -0.841471, 0, 0.997495, -0.0583741]

        NULL 保持在原位置：
        >>> isNull(direct_unary_sin(double([1, NULL])))
        [false, true]
        */
        return sin(col)
    }
    """
)

DIRECT_UNARY_SQRT = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_sqrt(col) {
        /*
        逐元素计算非负输入值的平方根。

        负数不在实数平方根定义域内，对应位置返回 NULL。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：仅非负数有定义；负数与 NULL 都返回 NULL。函数不会填充、删除或重排输入位置。

        形状与数值：标量输入返回标量，向量输入保持长度并逐元素计算。结果使用 DolphinDB
        浮点数学函数的精度和溢出规则。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 8.0
        >>> direct_unary_sqrt(col)
        [1, 1.41421, 2, 2.82843]

        非法定义域和 NULL 都产生缺失结果：
        >>> isNull(direct_unary_sqrt(double([-1, NULL, 4])))
        [true, true, false]
        */
        return sqrt(col)
    }
    """
)

DIRECT_UNARY_TAN = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_tan(col) {
        /*
        逐元素计算正切。

        Parameters
        ----------
        col : scalar or vector
            待计算的标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：输入位置为 NULL 时，同位置结果为 NULL；本算符不做填充或缺失值替换。

        形状与类型：标量输入返回标量，向量输入保持长度并逐元素计算；三角函数输入按弧度解释，不接受角度制标记。

        Examples
        --------
        >>> col = -2.5 -1.0 0.0 1.5 3.2
        >>> direct_unary_tan(col)
        [0.747022, -1.55741, 0, 14.1014, 0.0584739]

        NULL 保持在原位置：
        >>> isNull(direct_unary_tan(double([1, NULL])))
        [false, true]
        */
        return tan(col)
    }
    """
)

DIRECT_UNARY_WEEK = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_week(col) {
        /*
        从日期或时间值中提取年内周序号。

        Parameters
        ----------
        col : scalar or vector
            待提取的 DATE、TIMESTAMP 标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：时间值为 NULL 时，同位置结果为 NULL；布尔日期谓词也不会把缺失日期当作 false。

        输入约束：输入应为 DolphinDB temporal 类型。本算符不解析日期字符串，也不改变时区；结果采用对应
        DolphinDB 日历访问器的自然日定义，而不是交易日历。

        Examples
        --------
        >>> col = 2024.01.01 2024.02.29 2024.12.31
        >>> direct_unary_week(col)
        [1, 9, 1]

        缺失日期不会被解释为某个日历值：
        >>> isNull(direct_unary_week(date([2024.01.01, NULL])))
        [false, true]
        */
        return weekOfYear(col)
    }
    """
)

DIRECT_UNARY_WEEKDAY = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_weekday(col) {
        /*
        从日期或时间值中提取星期序号，星期一为 0。

        Parameters
        ----------
        col : scalar or vector
            待提取的 DATE、TIMESTAMP 标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：时间值为 NULL 时，同位置结果为 NULL；布尔日期谓词也不会把缺失日期当作 false。

        输入约束：输入应为 DolphinDB temporal 类型。本算符不解析日期字符串，也不改变时区；结果采用对应
        DolphinDB 日历访问器的自然日定义，而不是交易日历。

        Examples
        --------
        >>> col = 2024.01.01 2024.02.29 2024.12.31
        >>> direct_unary_weekday(col)
        [0, 3, 1]

        缺失日期不会被解释为某个日历值：
        >>> isNull(direct_unary_weekday(date([2024.01.01, NULL])))
        [false, true]
        */
        return weekday(col, false)
    }
    """
)

DIRECT_UNARY_YEAR = DolphinDBFunction(
    module="query",
    definition="""
    def direct_unary_year(col) {
        /*
        从日期或时间值中提取年份。

        Parameters
        ----------
        col : scalar or vector
            待提取的 DATE、TIMESTAMP 标量或向量。

        Returns
        -------
        result : scalar or vector[NUMBER]
            数值结果；向量输入按元素返回。

        Notes
        -----
        NULL 处理：时间值为 NULL 时，同位置结果为 NULL；布尔日期谓词也不会把缺失日期当作 false。

        输入约束：输入应为 DolphinDB temporal 类型。本算符不解析日期字符串，也不改变时区；结果采用对应
        DolphinDB 日历访问器的自然日定义，而不是交易日历。

        Examples
        --------
        >>> col = 2024.01.01 2024.02.29 2024.12.31
        >>> direct_unary_year(col)
        [2024, 2024, 2024]

        缺失日期不会被解释为某个日历值：
        >>> isNull(direct_unary_year(date([2024.01.01, NULL])))
        [false, true]
        */
        return year(col)
    }
    """
)

DIRECT_OPERATOR_FUNCTIONS = (
    DIRECT_BINARY_ADD,
    DIRECT_BINARY_AND,
    DIRECT_BINARY_DAYS_BETWEEN,
    DIRECT_BINARY_DIV,
    DIRECT_BINARY_EQ,
    DIRECT_BINARY_FLOOR_DIV,
    DIRECT_BINARY_GE,
    DIRECT_BINARY_GT,
    DIRECT_BINARY_LE,
    DIRECT_BINARY_LT,
    DIRECT_BINARY_MAXIMUM,
    DIRECT_BINARY_MINIMUM,
    DIRECT_BINARY_MOD,
    DIRECT_BINARY_MUL,
    DIRECT_BINARY_NE,
    DIRECT_BINARY_NULL_IF,
    DIRECT_BINARY_OR,
    DIRECT_BINARY_POW,
    DIRECT_BINARY_SUB,
    DIRECT_BINARY_XOR,
    DIRECT_MULTIARY_ADD,
    DIRECT_MULTIARY_AND,
    DIRECT_MULTIARY_COALESCE,
    DIRECT_MULTIARY_COUNT,
    DIRECT_MULTIARY_MAX,
    DIRECT_MULTIARY_MEAN,
    DIRECT_MULTIARY_MIN,
    DIRECT_MULTIARY_MUL,
    DIRECT_MULTIARY_OR,
    DIRECT_MULTIARY_STD,
    DIRECT_MULTIARY_VAR,
    DIRECT_NULLARY_FALSE,
    DIRECT_NULLARY_LITERAL,
    DIRECT_NULLARY_TRUE,
    DIRECT_TERNARY_WHERE,
    DIRECT_UNARY_ABS,
    DIRECT_UNARY_ACOS,
    DIRECT_UNARY_ASIN,
    DIRECT_UNARY_ATAN,
    DIRECT_UNARY_BETWEEN,
    DIRECT_UNARY_CAST,
    DIRECT_UNARY_CEIL,
    DIRECT_UNARY_CLIP,
    DIRECT_UNARY_COS,
    DIRECT_UNARY_DAY,
    DIRECT_UNARY_DAY_OF_YEAR,
    DIRECT_UNARY_EXP,
    DIRECT_UNARY_EXPM1,
    DIRECT_UNARY_FLOOR,
    DIRECT_UNARY_GET,
    DIRECT_UNARY_ISIN,
    DIRECT_UNARY_IS_FINITE,
    DIRECT_UNARY_IS_MONTH_END,
    DIRECT_UNARY_IS_NULL,
    DIRECT_UNARY_IS_QUARTER_END,
    DIRECT_UNARY_IS_WEEKEND,
    DIRECT_UNARY_IS_YEAR_END,
    DIRECT_UNARY_LOG,
    DIRECT_UNARY_LOG10,
    DIRECT_UNARY_LOG1P,
    DIRECT_UNARY_LOG2,
    DIRECT_UNARY_MONTH,
    DIRECT_UNARY_NEG,
    DIRECT_UNARY_NOT,
    DIRECT_UNARY_NOT_NULL,
    DIRECT_UNARY_QUARTER,
    DIRECT_UNARY_REPLACE,
    DIRECT_UNARY_ROUND,
    DIRECT_UNARY_SIGN,
    DIRECT_UNARY_SIN,
    DIRECT_UNARY_SQRT,
    DIRECT_UNARY_TAN,
    DIRECT_UNARY_WEEK,
    DIRECT_UNARY_WEEKDAY,
    DIRECT_UNARY_YEAR,
)
