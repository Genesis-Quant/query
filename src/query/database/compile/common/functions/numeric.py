"""数值算符共用的 DolphinDB 函数。"""

from query.database.compile import DolphinDBFunction

from .form import IS_SCALAR_FORM, IS_TABLE_FORM, IS_VECTOR_FORM

IS_FINITE_NUMBER = DolphinDBFunction(
    module="common",
    definition="""
    def is_finite_number(value) {
        // 逐元素判断有限数值，同时排除 NULL、NaN 和正负无穷。
        return isValid(value) && !isNanInf(double(value), true)
    }
    """
)

CONTROLS_REGRESSION = DolphinDBFunction(
    module="common",
    definition=r"""
    def controls_regression(target, controls, intercept) {
        /*
        内部回归辅助函数，不登记为 DSL 算符；CS 和每个 TS 窗口共用原中性化规则。

        Parameters
        ----------
        target : vector[NUMBER]
            回归因变量，允许 NULL；布尔值和非数值目标不作为连续收益处理。
        controls : table
            与 target 等行数的解释变量表，列顺序就是调用方给定的顺序。
            数值列直接进入设计矩阵；BOOL、STRING、SYMBOL 先独热编码，
            各分类列按类别值升序去掉第一个水平。类别缺失不是一个类别。
        intercept : bool
            正常回归是否包含截距项。

        Returns
        -------
        fit : dictionary
            valid 为目标和全部控制共同有效的行掩码，nobs 为有效行数；
            names/beta 按原控制列顺序排列，分类列按非基准类别升序展开。
            数值常量列保留系数位置且系数为 0，不进入实际拟合。
            alpha 为截距，residual 与 target 等长，无效行保留 DOUBLE NULL。

        Notes
        -----
        数值输入的 NULL、NaN、正负无穷共同排除，分类输入只排除 NULL。
        沿用原 CS 退化规则：无可用控制列、单样本或样本数不大于有效参数数时，
        退化为 y-avg(y)，alpha=avg(y)、beta=0；该退化规则不受 intercept 影响。
        正常拟合用 SVD 伪逆，秩亏列取最小范数最小二乘解；不取对数、不缩尾、不标准化。
        分类基准只来自当前截面或当前窗口，不读取未来类别。
        */
        if (!is_vector_form(target) || !is_table_form(controls))
            throw "回归 target 必须是向量，controls 必须是表"
        n = size(target)
        if (controls.rows() != n || controls.cols() == 0)
            throw "回归解释变量必须与 target 等长且至少有一列"
        if (!(type(target) in [CHAR, SHORT, INT, LONG, FLOAT, DOUBLE]))
            throw "回归 target 必须是数值"
        valid = is_finite_number(target)
        for (name in controls.columnNames()) {
            values = controls[name]
            if (type(values) in [BOOL, SYMBOL, STRING]) valid = valid && isValid(values)
            else valid = valid && is_finite_number(values)
        }
        fit = dict(STRING, ANY)
        fit["valid"] = valid
        fit["nobs"] = sum(valid)
        fit["alpha"] = double(NULL)
        fit["names"] = array(STRING, 0)
        fit["beta"] = array(DOUBLE, 0)
        fit["residual"] = take(double(NULL), n)
        if (sum(valid) == 0) return fit
        y = double(target[valid])
        x_table = controls[valid]
        categories = array(STRING, 0)
        names = array(STRING, 0)
        for (name in x_table.columnNames()) {
            if (type(x_table[name]) in [BOOL, SYMBOL, STRING]) {
                categories.append!(name)
                levels = sort(distinct(x_table[name]))
                if (size(levels) > 1) {
                    for (j in 1 .. (size(levels) - 1))
                        names.append!(name + "_" + string(levels[j]))
                }
            } else names.append!(name)
        }
        encoded = x_table
        if (size(categories) > 0) encoded = oneHot(x_table, symbol(categories))
        active = array(STRING, 0)
        for (name in names) {
            if (!(name in encoded.columnNames())) throw "回归分类编码列不存在：" + name
            if (size(distinct(encoded[name])) > 1) active.append!(name)
        }
        beta = take(0.0, size(names))
        alpha = avg(y)
        residual = y - alpha
        if (size(active) > 0 && size(y) > 1 && size(y) > size(active) + int(intercept)) {
            design = array(ANY, 0)
            if (intercept) design.append!(take(1.0, size(y)))
            for (name in active) design.append!(double(encoded[name]))
            coefficients = (pinv(matrix(design)) ** matrix(y))[0]
            alpha = 0.0
            if (intercept) alpha = coefficients[0]
            fitted = take(alpha, size(y))
            for (j in 0 .. (size(active) - 1)) {
                position = find(names, active[j])
                beta[position] = coefficients[j + int(intercept)]
                fitted += beta[position] * double(encoded[active[j]])
            }
            residual = y - fitted
        }
        values = fit["residual"]
        values[valid] = residual
        fit["alpha"] = alpha
        fit["names"] = names
        fit["beta"] = beta
        fit["residual"] = values
        return fit
    }
    """,
    dependencies=(IS_FINITE_NUMBER, IS_TABLE_FORM, IS_VECTOR_FORM),
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

BROADCAST_LIKE = DolphinDBFunction(
    module="common",
    definition="""
def broadcast_like(value, reference) {
    // 将标量 value 广播到与 reference 相同的长度。
    return take(value, size(reference))
}
"""
)

CROSS_SECTION_RANK = DolphinDBFunction(
    module="common",
    definition="""
def cross_section_rank(value, ascending, ties_method, percent) {
    // 统一普通、密集和百分位截面排名，并将非百分位名次调整为从 1 开始。
    if (ties_method == "dense") {
        result = denseRank(value, ascending, true, percent)
    } else {
        result = rank(value, ascending, , true, ties_method, percent)
    }
    if (!percent) result = result + 1
    return result
}
"""
)

CROSS_SECTION_SLOPE = DolphinDBFunction(
    module="common",
    definition="""
def cross_section_slope(left, right) {
    // 计算 right 关于 left 的截面 OLS 斜率；自变量无方差时返回 NULL。
    valid = isValid(left) && isValid(right)
    paired_left = iif(valid, double(left), double(NULL))
    paired_right = iif(valid, double(right), double(NULL))
    variance = covar(paired_left, paired_left)
    return iif(
        isNull(variance) || variance == 0,
        double(NULL),
        covar(paired_left, paired_right) / variance
    )
}
"""
)

ROLLING_MIN_PERIODS = DolphinDBFunction(
    module="common",
    definition="""
    def rolling_min_periods(window, min_periods) {
        // 规范化滚动窗口的最少观测数；NULL 表示要求完整 window。
        if (isNull(min_periods)) return int(window)
        return int(min_periods)
    }
    """
)

MASK_EXPANDING_RESULT = DolphinDBFunction(
    module="common",
    definition="""
    def mask_expanding_result(result, value, min_periods) {
        // 在累计有效观测数达到 min_periods 前，将单序列 expanding 结果置为 NULL。
        return iif(cumcount(value) < int(min_periods), NULL, result)
    }
    """
)

MASK_PAIR_EXPANDING_RESULT = DolphinDBFunction(
    module="common",
    definition="""
    def mask_pair_expanding_result(result, left, right, min_periods) {
        // 仅统计左右两列同时有效的样本，并遮蔽观测不足的双序列 expanding 结果。
        valid = iif(isValid(left) && isValid(right), 1, int(NULL))
        return iif(cumcount(valid) < int(min_periods), NULL, result)
    }
    """
)

ROLLING_SLOPE = DolphinDBFunction(
    module="common",
    definition="""
    def rolling_slope(left, right, window, min_periods) {
        // 计算 right 关于 left 的滚动 OLS 斜率。
        return mbeta(right, left, int(window), int(min_periods))
    }
    """
)

ROLLING_INTERCEPT = DolphinDBFunction(
    module="common",
    definition="""
    def rolling_intercept(left, right, window, min_periods) {
        // 仅使用左右两列同时有效的样本均值计算 right 关于 left 的 OLS 截距。
        valid = isValid(left) && isValid(right)
        paired_left = iif(valid, double(left), double(NULL))
        paired_right = iif(valid, double(right), double(NULL))
        slope = rolling_slope(left, right, window, min_periods)
        return mavg(paired_right, int(window), int(min_periods)) - slope * mavg(paired_left, int(window), int(min_periods))
    }
    """,
    dependencies=(ROLLING_SLOPE,),
)

ROLLING_CONTROLS_REGRESSION = DolphinDBFunction(
    module="common",
    definition=r"""
    def rolling_controls_regression(target, controls, window, min_periods, intercept) {
        /*
        内部滚动回归辅助函数，不登记为算符；为三个标量输出共用每个窗口的同一次拟合。

        Parameters
        ----------
        target : vector[NUMBER]
            一只证券已按时间升序排列的目标序列。
        controls : table
            同行数的有序解释变量；允许连续、BOOL、STRING、SYMBOL，各窗口独立编码。
        window : int
            右对齐的观测行窗口，包含当前行；缺失行占窗口位置，不向前凑样本。
        min_periods : int or NULL
            最少共同有效观测数，NULL 等于 window；不足时该窗口所有输出为 NULL。
        intercept : bool
            正常回归是否含截距；其余编码和退化规则与 controls_regression 相同。

        Returns
        -------
        result : table
            内部使用的 alpha、residual、beta0...数值列；每行对应原输入位置。
            residual 只取当前行在当前窗口拟合下的残差，不返回整个窗口残差数组。

        Notes
        -----
        alpha/beta 可在当前行缺失但窗口仍有足够共同样本时有效；当前残差仍为 NULL。
        分类展开列顺序由当前窗口决定，无未来类别；该窗口不存在的系数位置为 NULL。
        不输出矩阵或数组因子，不将每次回归残差重新应用于以后的窗口。
        */
        if (!is_vector_form(target) || !is_table_form(controls) || controls.rows() != size(target) || controls.cols() == 0)
            throw "回归 target 和 controls 必须等长且解释变量非空"
        minimum = rolling_min_periods(window, min_periods)
        if (isNull(window) || window < 1 || window != int(window) || minimum < 1 || minimum > window)
            throw "滚动回归窗口参数无效"
        n = size(target)
        output = dict(STRING, ANY)
        output["alpha"] = take(double(NULL), n)
        output["residual"] = take(double(NULL), n)
        if (n == 0) return transpose(output)
        for (i in 0 .. (n - 1)) {
            indices = max(0, i - int(window) + 1) .. i
            fit = controls_regression(target[indices], controls[indices], intercept)
            if (fit.nobs < minimum) continue
            values = output["alpha"]
            values[i] = fit.alpha
            output["alpha"] = values
            values = output["residual"]
            values[i] = last(fit.residual)
            output["residual"] = values
            if (size(fit.beta) > 0) {
                for (j in 0 .. (size(fit.beta) - 1)) {
                    name = "beta" + string(j)
                    if (!(name in output)) output[name] = take(double(NULL), n)
                    values = output[name]
                    values[i] = fit.beta[j]
                    output[name] = values
                }
            }
        }
        return transpose(output)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS, CONTROLS_REGRESSION, IS_TABLE_FORM, IS_VECTOR_FORM),
)

ROLLING_TRUE_COUNT = DolphinDBFunction(
    module="common",
    definition="""
    def rolling_true_count(value, window, min_periods) {
        // 将 NULL 按 false 处理，统计每个滚动窗口中的 true 数量。
        if (type(value) != BOOL) throw "条件型算符的 col 必须是 BOOL"
        return msum(int(nullFill(value, false)), int(window), int(min_periods))
    }
    """
)

TALIB_MOVING_AVERAGE = DolphinDBFunction(
    module="common",
    definition="""
    def talib_moving_average(value, time_period, ma_type) {
        // 按 TA-Lib MAType 计算均线；T3 显式使用标准默认参数 vfactor=0.7。
        if (int(ma_type) == 8) return ta::t3(value, int(time_period), 0.7)
        return ta::ma(value, int(time_period), int(ma_type))
    }
    """
)
