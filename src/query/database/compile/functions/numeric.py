"""数值算符共用的 DolphinDB 函数。"""

from .form import IS_DICTIONARY_FORM, IS_SCALAR_FORM, IS_TABLE_FORM, IS_VECTOR_FORM
from .function import DolphinDBFunction

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
    def controls_regression(target, controls, intercept, method="ols", weights=NULL, binary=false) {
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
        method : string, default "ols"
            ols 为等权拟合；wls 最小化 sum(weights * residual^2)，不改变 CS 默认行为。
        weights : numeric vector or NULL
            WLS 与输入等长的有限非负目标权重；0 权重不影响拟合目标，但有效行残差仍参与普通标准差。
        binary : bool, default false
            内部二元回归模式；少于两个配对或自变量无方差时返回 NULL，不用多元去均值退化。

        Returns
        -------
        fit : dictionary
            valid 为目标和全部控制共同有效的行掩码，nobs 为有效行数；
            names/beta 按原控制列顺序排列，分类列按非基准类别升序展开。
            数值常量列保留系数位置且系数为 0，不进入实际拟合。
            alpha 为截距，residual 与 target 等长，无效行保留 DOUBLE NULL。
            residual_std 为本次拟合全部有效残差的样本标准差（ddof=1），不足两条为 NULL；
            WLS 也取普通残差标准差，不取加权标准差或按回归参数数修正的标准误。

        Notes
        -----
        数值输入的 NULL、NaN、正负无穷共同排除，分类输入只排除 NULL。
        沿用原 CS 退化规则：无可用控制列、单样本或样本数不大于有效参数数时，
        退化为 y-avg(y)，alpha=avg(y)、beta=0；该退化规则不受 intercept 影响。
        WLS 的退化均值和设计矩阵只使用正权重样本；零权重行只参与残差输出及标准差。
        binary=true 不使用多元退化规则；正常拟合按当前窗口中心化并缩放。
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
        if (!(method in ["ols", "wls"])) throw "回归 method 必须为 ols 或 wls"
        if (method == "ols" && type(weights) != VOID) throw "OLS 不接受 weights"
        if (binary && (controls.cols() != 1 || !(type(controls[controls.columnNames()[0]]) in [CHAR, SHORT, INT, LONG, FLOAT, DOUBLE])))
            throw "二元回归必须有一个数值自变量"
        valid = is_finite_number(target)
        if (method == "wls") {
            if (!is_vector_form(weights) || size(weights) != n) throw "WLS weights 必须与 target 等长"
            if (!(type(weights) in [CHAR, SHORT, INT, LONG, FLOAT, DOUBLE])) throw "WLS weights 必须是数值"
            if (any(!is_finite_number(weights)) || any(weights < 0)) throw "WLS weights 必须有限且非负"
        }
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
        fit["residual_std"] = double(NULL)
        if (sum(valid) == 0) return fit
        y = double(target[valid])
        selected_weights = take(1.0, size(y))
        if (method == "wls") {
            selected_weights = double(weights[valid])
            if (!any(selected_weights > 0)) return fit
            selected_weights /= max(selected_weights)
        }
        positive = selected_weights > 0
        fit_count = sum(positive)
        x_table = controls[valid]
        categories = array(STRING, 0)
        names = array(STRING, 0)
        for (name in x_table.columnNames()) {
            if (type(x_table[name]) in [BOOL, SYMBOL, STRING]) {
                categories.append!(name)
                levels = sort(distinct(x_table[name][positive]))
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
            if (size(distinct(encoded[name][positive])) > 1) active.append!(name)
        }
        if (binary && (fit_count < 2 || size(active) == 0)) return fit
        beta = take(0.0, size(names))
        alpha = wavg(y[positive], selected_weights[positive])
        residual = y - alpha
        if (size(active) > 0 && fit_count > 1 && (binary || fit_count > size(active) + int(intercept))) {
            if (method == "wls" || binary) {
                // 只用正权重样本拟合，按当前窗口中心化和缩放，避免大数与截距的数值秩丢失。
                weight_scale = sqrt(selected_weights[positive])
                target_origin = 0.0
                target_offset = 0.0
                if (intercept) {
                    target_origin = first(y[positive])
                    target_offset = wavg(y[positive] - target_origin, selected_weights[positive])
                }
                centered_target = (y - target_origin) - target_offset
                fit_target = centered_target[positive] * weight_scale
                design = array(ANY, 0)
                centered_columns = array(ANY, 0)
                centers = array(DOUBLE, 0)
                scale = 0.0
                for (name in active) {
                    values = double(encoded[name])
                    origin = 0.0
                    offset = 0.0
                    if (intercept) {
                        origin = first(values[positive])
                        offset = wavg(values[positive] - origin, selected_weights[positive])
                    }
                    centered = (values - origin) - offset
                    centers.append!(origin + offset)
                    centered_columns.append!(centered)
                    scale = max(scale, max(abs(centered[positive])))
                }
                for (centered in centered_columns)
                    design.append!((centered[positive] / scale) * weight_scale)
                coefficients = (pinv(matrix(design)) ** matrix(fit_target))[0]
                alpha = target_origin + target_offset
                residual = centered_target
                for (j in 0 .. (size(active) - 1)) {
                    coefficient = coefficients[j] / scale
                    beta[find(names, active[j])] = coefficient
                    alpha -= coefficient * centers[j]
                    residual -= coefficient * centered_columns[j]
                }
            } else {
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
        }
        values = fit["residual"]
        values[valid] = residual
        fit["alpha"] = alpha
        fit["names"] = names
        fit["beta"] = beta
        fit["residual"] = values
        fit["residual_std"] = std(residual)
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
                // 每个值独立解析秒/毫秒格式；NULL 和空向量保持原形状，不由首行决定格式。
                precise = timestamp(temporalParse(value, "yyyy-MM-ddTHH:mm:ss.SSS"))
                seconds = timestamp(temporalParse(value, "yyyy-MM-ddTHH:mm:ss"))
                return nullFill(precise, seconds)
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

ROW_REDUCTION = DolphinDBFunction(
    module="common",
    definition=r"""
    def row_reduction(cols, operation, ddof=1) {
        /*
        对标量和等长向量组成的操作数执行逐行数值归约，不改变输入。

        Parameters
        ----------
        cols : ANY vector
            非空操作数列表；标量广播到向量长度，全标量输入视作单行。
        operation : string
            add、mean、min、max、mul、count、std 或 var。
        ddof : int, default 1
            std/var 的自由度修正，只允许 0 或 1。

        Returns
        -------
        result : scalar or vector
            全标量返回标量；其余返回等长向量，空向量返回空结果。

        Notes
        -----
        NULL 不参与归约；全部缺失时 count 为 0，其余为 NULL。
        方差先中心化再平方，不调用可能被 ta 模块遮蔽的 var。
        不同长度向量拒绝计算，不能用广播掩盖输入错误。

        Examples
        --------
        >>> row_reduction([1.0, 2.0, 3.0], "var", 1)
        1
        >>> row_reduction([1.0 2.0, 3.0], "add")
        [4, 5]
        */
        if (size(cols) == 0) throw "逐行归约至少需要一个操作数"
        scalar = true
        n = 1
        for (col in cols) {
            if (is_vector_form(col)) {
                if (!scalar && size(col) != n) throw "逐行归约的向量必须等长"
                n = size(col)
                scalar = false
            } else if (!is_scalar_form(col)) throw "逐行归约只接受标量或向量"
        }
        values = array(ANY, 0)
        for (col in cols) {
            value = col
            if (type(value) == VOID) value = double(NULL)
            if (is_scalar_form(value)) value = take(value, n)
            values.append!(value)
        }
        if (operation == "add") result = unifiedCall(rowSum, values)
        else if (operation == "mean") result = unifiedCall(rowAvg, values)
        else if (operation == "min") result = unifiedCall(rowMin, values)
        else if (operation == "max") result = unifiedCall(rowMax, values)
        else if (operation == "mul") result = unifiedCall(rowProd, values)
        else if (operation == "count") result = unifiedCall(rowCount, values)
        else if (operation in ["std", "var"]) {
            if (!(ddof in [0, 1])) throw "方差自由度只允许 0 或 1"
            means = unifiedCall(rowAvg, values)
            counts = unifiedCall(rowCount, values)
            squared = array(ANY, 0)
            for (value in values) {
                centered = double(value) - means
                squared.append!(centered * centered)
            }
            result = iif(counts > ddof, unifiedCall(rowSum, squared) / double(counts - ddof), double(NULL))
            if (operation == "std") result = sqrt(result)
        } else throw "未知逐行归约：" + operation
        if (scalar) return result[0]
        return result
    }
    """,
    dependencies=(IS_SCALAR_FORM, IS_VECTOR_FORM),
)

REPLACE_VALUES = DolphinDBFunction(
    module="common",
    definition=r"""
    def replace_values(col, old, new) {
        /*
        按列表顺序替换，比较原始匹配值并对数值结果执行无窄化类型提升。

        Parameters
        ----------
        col : scalar or vector
            待替换输入，不就地修改。
        old, new : vector
            非空等长映射；NULL 可以作为匹配值或替换值。

        Returns
        -------
        result : scalar or vector
            形状与 col 相同；数值按 col/new 的最宽类型，字符串保留字符含义。

        Notes
        -----
        替换按顺序级联；不把 old 强制转成输入类型而改变匹配关系。
        数值与文本之间没有无损公共类型时明确报错，不静默转为 NULL。
        NULL 匹配使用 isNull，未命中的缺失值仍为缺失。

        Examples
        --------
        >>> replace_values(1 2 3, [1], [1.5])
        [1.5, 2, 3]
        >>> replace_values(1 2 3, [1.5], [0])
        [1, 2, 3]
        */
        if (size(old) == 0 || size(old) != size(new)) throw "old/new 必须非空且等长"
        numeric_types = [BOOL, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE]
        target_type = type(col)
        numeric = target_type in numeric_types
        text = target_type in [STRING, SYMBOL]
        for (replacement in new) {
            if (isNull(replacement)) continue
            if (numeric) {
                if (!(type(replacement) in numeric_types)) throw "数值替换值必须是数值或 NULL"
                target_type = max(target_type, type(replacement))
            } else if (text) {
                if (!(type(replacement) in [STRING, SYMBOL])) throw "字符串替换值必须是字符串或 NULL"
            } else if (type(replacement) != target_type) throw "替换值类型与输入不兼容"
        }
        result = cast(col, target_type)
        replaced_at = take(-1, size(col))
        if (is_scalar_form(col)) replaced_at = -1
        for (i in 0 : size(old)) {
            original = old[i]
            if (!isNull(original)) {
                if (numeric && !(type(original) in numeric_types)) throw "数值匹配值必须是数值或 NULL"
                if (text && !(type(original) in [STRING, SYMBOL])) throw "字符串匹配值必须是字符串或 NULL"
            }
            // 输出提升不能使尚未替换的大整数在比较时先损失精度。
            matched = isNull(col)
            if (!isNull(original)) matched = nullFill(col == original, false)
            matched = matched && (replaced_at == -1)
            for (previous in 0 : i) {
                same = isNull(new[previous]) && isNull(original)
                if (!isNull(new[previous]) && !isNull(original)) same = new[previous] == original
                if (same) matched = matched || (replaced_at == previous)
            }
            replacement = new[i]
            if (isNull(replacement)) replacement = cast(NULL, target_type)
            else replacement = cast(replacement, target_type)
            result = iif(matched, replacement, result)
            replaced_at = iif(matched, i, replaced_at)
        }
        return result
    }
    """,
    dependencies=(IS_SCALAR_FORM,),
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
        // 整数窗口默认要求完整条数，日历窗口无法推算条数，默认至少一个有效观测。
        if (isNull(min_periods)) {
            if (type(window) == STRING) return 1
            return int(window)
        }
        return int(min_periods)
    }
    """
)

NORMALIZE_CALENDAR_WINDOW = DolphinDBFunction(
    module="common",
    definition=r"""
    def normalize_calendar_window(window) {
        // h/H均表示小时；m为分钟，M为日历月。只规范单位，不换算日历跨度。
        if (type(window) != STRING || regexFind(window, "^[1-9][0-9]*(ms|s|m|h|H|d|w|M|y)$") != 0)
            throw "window必须为正整数条数或带单位的正日历跨度"
        return strReplace(window, "h", "H")
    }
    """,
)

CALENDAR_WINDOW_SPANS = DolphinDBFunction(
    module="common",
    definition=r"""
    def calendar_window_spans(time, window) {
        /* 按实际时间计算右闭左开窗口的行数，保留此前同一时点的观测。
         * M/y使用日历月年，不换算成固定天数；on筛选由调用方在本函数之前完成。
         */
        period = normalize_calendar_window(window)
        if (any(isNull(time))) throw "日历窗口的time不能包含NULL"
        if (size(time) == 0) return long([])
        ordered = timestamp(time)
        if (any(deltas(ordered)[1:] < 0)) throw "日历窗口的time必须升序"
        return long(tmcount(ordered, take(1, size(time)), duration(period)))
    }
    """,
    dependencies=(NORMALIZE_CALENDAR_WINDOW,),
)

WEIGHTED_ROLLING_MEAN = DolphinDBFunction(
    module="common",
    definition=r"""
    def weighted_rolling_mean(col, time, window, min_periods, weights) {
        /* 有限窗口位置权重；先按原窗口对齐，再跳过NULL，不用无限历史EWM近似。 */
        if (size(col) != size(time)) throw "加权滚动输入与time必须等长"
        if (size(col) == 0) return double([])
        if (size(weights) == 0 || any(!is_finite_number(weights)) || any(weights < 0) || !any(weights > 0))
            throw "滚动权重必须非空、有限、非负且至少一项大于0"
        minimum = rolling_min_periods(window, min_periods)
        result = take(double(NULL), size(col))
        pending = size(col)
        if (type(window) != STRING) {
            if (size(weights) != int(window)) throw "滚动权重长度必须等于window"
            if (int(window) == 1) return double(col)
            if (int(window) <= 1024) {
                result = mavg(col, double(weights), minimum)
                if (minimum == int(window)) return result
                // 向量权重mavg不计算前置短窗口；仅补这些位置，完整窗口仍用原生内核。
                pending = min(size(col), int(window)-1)
            } else if (minimum == int(window)) return moving(wavg{,double(weights)}, col, int(window), minimum)
            positions = 1..size(col)
            spans = long(iif(positions > int(window), int(window), positions))
        } else spans = calendar_window_spans(time, window)
        if (max(spans) > size(weights)) throw "日历窗口的观测数超过weights长度"
        for (i in 0 : pending) {
            values = col[(i-spans[i]+1):(i+1)]
            if (count(values) < minimum) continue
            current_weights = double(weights[(size(weights)-size(values)):size(weights)])
            result[i] = wavg(values, current_weights)
        }
        return result
    }
    """,
    dependencies=(CALENDAR_WINDOW_SPANS, ROLLING_MIN_PERIODS, IS_FINITE_NUMBER),
)

CALENDAR_WINDOW_VALUE = DolphinDBFunction(
    module="common",
    definition=r"""
    def calendar_window_value(operation, minimum, values) {
        // 原生tm内核没有覆盖的归约；权重和位置均以当前窗口中的真实观测行定义。
        if (count(values) < minimum) return double(NULL)
        if (operation == "rolling_argmax") return double(imax(values))
        if (operation == "rolling_argmin") return double(imin(values))
        if (operation == "rolling_mad") return median(abs(values - median(values)))
        if (operation == "decay_linear") {
            if (size(values) > 1024) throw "线性衰减窗口最多为1024条观测"
            return wavg(values, double(1..size(values)))
        }
        throw "未知日历窗口归约：" + operation
    }
    """,
)

CALENDAR_ROLLING_UNARY = DolphinDBFunction(
    module="common",
    definition=r"""
    def calendar_rolling_unary(col, time, window, min_periods, operation, q=0.5, ascending=true, ties_method="min") {
        /* 与现有rolling算符共用名称和NULL语义，仅将窗口边界切换为时间跨度。
         * 日历窗口min_periods默认1，仍按非NULL观测计数，不要求先经过完整日历跨度。
         * first/last保留物理端点，rank当前位置为NULL时仍返回NULL。
         */
        period = normalize_calendar_window(window)
        spans = calendar_window_spans(time, period)
        if (size(col) != size(time)) throw "日历窗口输入与time必须等长"
        if (size(col) == 0) return col
        minimum = rolling_min_periods(window, min_periods)
        if (minimum < 1) throw "min_periods必须为正整数"
        dates = timestamp(time)
        counts = tmcount(dates, col, duration(period))
        if (operation in ["rolling_all", "rolling_any", "rolling_true_count"]) {
            if (type(col) != BOOL) throw "条件型算符的col必须是BOOL"
            truths = tmsum(dates, int(nullFill(col, false)), duration(period))
            if (operation == "rolling_all") return (counts >= minimum) && (truths == counts)
            if (operation == "rolling_any") return (spans >= minimum) && (truths > 0)
            return iif(spans >= minimum, double(truths), double(NULL))
        }
        if (operation == "rolling_count") result = double(counts)
        else if (operation == "rolling_sum") result = tmsum(dates, col, duration(period))
        else if (operation == "rolling_mean") result = tmavg(dates, col, duration(period))
        else if (operation == "rolling_std") result = tmstd(dates, col, duration(period))
        else if (operation == "rolling_var") result = tmvar(dates, col, duration(period))
        else if (operation == "rolling_min") result = tmmin(dates, col, duration(period))
        else if (operation == "rolling_max") result = tmmax(dates, col, duration(period))
        else if (operation == "rolling_prod") result = tmprod(dates, col, duration(period))
        else if (operation == "rolling_first") result = tmfirst(dates, col, duration(period))
        else if (operation == "rolling_last") result = tmlast(dates, col, duration(period))
        else if (operation == "rolling_median") result = tmmed(dates, col, duration(period))
        else if (operation == "rolling_quantile") result = tmpercentile(dates, col, 100*q, duration(period), "linear")
        else if (operation == "rolling_skew") result = tmskew(dates, col, duration(period), true)
        else if (operation == "rolling_kurt") result = tmkurtosis(dates, col, duration(period), true)
        else if (operation == "rolling_sem") result = tmstd(dates, col, duration(period)) / sqrt(counts)
        else if (operation == "rolling_zscore") {
            scale = tmstd(dates, col, duration(period))
            result = iif(scale == 0, double(NULL), (col - tmavg(dates, col, duration(period))) / scale)
        } else if (operation in ["rolling_rank", "rolling_rank_pct"]) {
            percent = operation == "rolling_rank_pct"
            result = tmrank(dates, col, ascending, duration(period), true, ties_method, percent)
            if (!percent) result += 1
        } else {
            result = take(double(NULL), size(col))
            for (i in 0 : size(col)) {
                if (counts[i] < minimum) continue
                values = col[(i - spans[i] + 1):(i + 1)]
                result[i] = calendar_window_value(operation, minimum, values)
            }
        }
        return iif(counts >= minimum, result, double(NULL))
    }
    """,
    dependencies=(CALENDAR_WINDOW_SPANS, CALENDAR_WINDOW_VALUE, ROLLING_MIN_PERIODS),
)

CALENDAR_ROLLING_PAIR = DolphinDBFunction(
    module="common",
    definition=r"""
    def calendar_rolling_pair(left, right, time, window, min_periods, operation) {
        // 二元回归方向与整数窗口相同：right对left；最少观测数只统计共同有效配对。
        period = normalize_calendar_window(window)
        spans = calendar_window_spans(time, period)
        if (size(left) != size(time) || size(right) != size(time)) throw "日历窗口双序列必须与time等长"
        if (size(time) == 0) return double([])
        minimum = rolling_min_periods(window, min_periods)
        if (minimum < 1) throw "min_periods必须为正整数"
        dates = timestamp(time)
        valid = isValid(left) && isValid(right)
        x = iif(valid, double(left), double(NULL))
        y = iif(valid, double(right), double(NULL))
        counts = tmcount(dates, x, duration(period))
        if (operation == "rolling_corr") result = tmcorr(dates, x, y, duration(period))
        else if (operation == "rolling_cov") result = tmcovar(dates, x, y, duration(period))
        else {
            slope = tmbeta(dates, y, x, duration(period))
            if (operation == "rolling_beta") result = slope
            else {
                intercept = tmavg(dates, y, duration(period)) - slope * tmavg(dates, x, duration(period))
                if (operation == "rolling_alpha") result = intercept
                else if (operation == "rolling_residual") result = right - intercept - slope * left
                else throw "未知日历窗口双序列算符：" + operation
            }
        }
        return iif(counts >= minimum, result, double(NULL))
    }
    """,
    dependencies=(CALENDAR_WINDOW_SPANS, ROLLING_MIN_PERIODS),
)

ROLLING_SINGLETON = DolphinDBFunction(
    module="common",
    definition=r"""
    def rolling_singleton(col, operation) {
        /*
        处理 window=1 的滚动退化值，避免调用要求 window>=2 的移动内核。

        Parameters
        ----------
        col : vector
            按时间排序的单列；条件归约由算符保证为 BOOL。
        operation : string
            value、zero、rank、count_true、bool 或 undefined。

        Returns
        -------
        result : vector
            与输入等长；value 保留原类型，bool 返回 BOOL，其他结果为 DOUBLE。

        Notes
        -----
        单观测的样本方差、标准差、相关、回归和高阶矩无定义，返回 NULL。
        排名为 1，端点位置与 MAD 为 0；条件归约的 NULL 按 false，其余保持缺失。
        空向量返回相同长度的空结果，不读取其他日期或证券。

        Examples
        --------
        >>> rolling_singleton(1.0 NULL 3.0, "rank")
        [1, NULL, 1]
        >>> rolling_singleton(true false NULL, "count_true")
        [1, 0, 0]
        */
        if (operation in ["bool", "count_true"] && type(col) != BOOL) throw "条件型算符的 col 必须是 BOOL"
        if (operation == "value") return col
        if (operation == "bool") return nullFill(col, false)
        if (operation == "count_true") return double(nullFill(col, false))
        if (operation == "zero") return iif(isNull(col), double(NULL), 0.0)
        if (operation == "rank") return iif(isNull(col), double(NULL), 1.0)
        if (operation == "undefined") return take(double(NULL), size(col))
        throw "未知单观测滚动结果：" + operation
    }
    """,
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

NORMALIZE_REGRESSION_FILL = DolphinDBFunction(
    module="common",
    definition=r"""
    def normalize_regression_fill(fill, count) {
        /*
        规范化内部填充配置，不登记为算符；调用方省略参数时传入 "ffill"。

        Parameters
        ----------
        fill : string, dictionary or NULL
            NULL 关闭全部填充；ffill/mean 或 method 规则应用所有列；
            target/controls 对象分别配置，省略项默认 ffill；也接受内部规范化结果。
        count : int
            有序解释变量数量，不包含目标；controls 列表必须与它等长。

        Returns
        -------
        config : dictionary
            methods 为目标加有序控制的 STRING 向量，空字符串表示该列不填；
            values 为对应常量的 ANY 列表，非 constant 的项统一为 VOID NULL。

        Notes
        -----
        列表内 NULL 表示该列不填。常量必须显式指定且非 NULL；不支持未来回填。
        同义配置归一后用于共享拟合缓存，不同方法或常量不得共享错误的结果。
        不读取行情、不猜测股票池，不将 fill 名称解释为列引用。

        Examples
        --------
        >>> normalize_regression_fill("ffill", 1).methods
        ["ffill", "ffill"]
        >>> normalize_regression_fill(NULL, 1).methods
        ["", ""]
        >>> normalize_regression_fill(fromStdJson('{"target":null,"controls":["mean"]}'), 1).methods
        ["", "mean"]
        */
        if (is_dictionary_form(fill) && "methods" in fill && "values" in fill) {
            if (size(fill.methods) != count + 1 || size(fill.values) != count + 1)
                throw "规范化 fill 必须与目标和解释变量等长"
            return fill
        }
        rules = array(ANY, 0)
        for (i in 0 : (count + 1)) rules.append!(fill)
        if (is_dictionary_form(fill) && !("method" in fill)) {
            rules = array(ANY, 0)
            for (i in 0 : (count + 1)) rules.append!("ffill")
            if ("target" in fill) rules[0] = fill["target"]
            if ("controls" in fill && type(fill["controls"]) != VOID) {
                controls_fill = fill["controls"]
                if (!is_vector_form(controls_fill) || size(controls_fill) != count)
                    throw "fill.controls 必须与回归解释变量等长"
                for (i in 0 : count) rules[i + 1] = controls_fill[i]
            }
        }
        methods = take("", count + 1)
        values = array(ANY, 0)
        for (i in 0 : (count + 1)) {
            rule = rules[i]
            method = ""
            if (type(rule) != VOID) {
                if (is_dictionary_form(rule)) {
                    if (!("method" in rule)) throw "fill 单列规则缺少 method"
                    method = rule["method"]
                } else if (is_scalar_form(rule) && type(rule) == STRING) method = rule
                else throw "fill 必须为 NULL、ffill、mean、constant 规则或逐列配置"
                if (!(method in ["constant", "ffill", "mean"])) throw "不支持的回归 fill 方法"
                if (method == "constant") {
                    if (!is_dictionary_form(rule)) throw "constant 填充必须提供非 NULL 的 value"
                    if (!("value" in rule)) throw "constant 填充必须提供非 NULL 的 value"
                    if (isNull(rule["value"])) throw "constant 填充必须提供非 NULL 的 value"
                } else if (is_dictionary_form(rule)) {
                    if ("value" in rule) {
                        if (!isNull(rule["value"])) throw "只有 constant 填充允许指定 value"
                    }
                }
            }
            methods[i] = method
            if (method == "constant") values.append!(rule["value"])
            else values.append!(NULL)
        }
        return dict(`methods`values, [methods, values])
    }
    """,
    dependencies=(IS_DICTIONARY_FORM, IS_SCALAR_FORM, IS_VECTOR_FORM),
)

FILL_REGRESSION_COLUMN = DolphinDBFunction(
    module="common",
    definition=r"""
    def fill_regression_column(col, method, value, code, time, target) {
        /*
        内部单列填充，在确定窗口前处理当前节点的参与行，不改变外层列。

        Parameters
        ----------
        col : vector
            数值目标或连续/BOOL/STRING/SYMBOL 控制；行数与 code/time 一致。
        method : string
            空字符串不填；constant 用 value，ffill 沿各股票已加载历史，mean 用同日截面。
        value : scalar or NULL
            constant 的同类型常量；数值可用整数或浮点，但不把分类转成连续值。
        code, time : vector
            当前节点 on=true 的参与行；ffill 按证券、日期，mean 只使用相同日期。
        target : bool
            true 时 col 必须为数值目标，BOOL 不当作连续目标。

        Returns
        -------
        result : vector
            数值列转为 DOUBLE；分类列保持类型。None 不填且保持原值；其它方法先将
            数值 NULL/NaN/Inf 视作缺失。ffill 头部、mean 整个截面无有效值时仍为 NULL。

        Notes
        -----
        mean 不跨日期、不跨字段，只使用本列该日原始有限数值，不做递归填补；
        BOOL/STRING/SYMBOL 的 mean 明确报错。ffill 不使用未来数据或区间外 seed。
        填充值会参与 min_periods 和当天残差，不是只填输出，也不填已算出的残差。

        Examples
        --------
        >>> fill_regression_column(1.0 NULL 3 NULL, "ffill", NULL, `A`A`B`B, 1 2 1 2, true)
        [1, 1, 3, 3]
        >>> fill_regression_column(1.0 NULL 3 NULL, "mean", NULL, `A`B`A`B, 1 1 2 2, true)
        [1, 1, 3, 3]
        >>> fill_regression_column(1.0 NULL, "constant", 0.0, `A`A, 1 2, true)
        [1, 0]
        */
        numeric = type(col) in [CHAR, SHORT, INT, LONG, FLOAT, DOUBLE]
        categorical = type(col) in [BOOL, SYMBOL, STRING]
        if (target && !numeric) throw "回归 target 必须是数值"
        if (!numeric && !categorical) throw "回归解释变量必须是数值或 BOOL/STRING/SYMBOL"
        if (method == "") return col
        values = col.copy()
        if (numeric) values = iif(is_finite_number(col), double(col), double(NULL))
        if (method == "constant") {
            if (numeric) {
                if (!(type(value) in [CHAR, SHORT, INT, LONG, FLOAT, DOUBLE]) || !is_finite_number(value))
                    throw "数值回归列的 constant 必须是有限数值且不能是 BOOL"
                return nullFill(values, double(value))
            }
            if (type(col) == BOOL) {
                if (type(value) != BOOL) throw "BOOL 控制列的 constant 必须是 BOOL"
                return nullFill(values, value)
            }
            if (!(type(value) in [STRING, SYMBOL])) throw "STRING/SYMBOL 控制列的 constant 必须是字符串类别"
            result = nullFill(string(values), string(value))
            if (type(col) == SYMBOL) return symbol(result)
            return result
        }
        if (method == "mean" && !numeric) throw "mean 截面均值填充不支持分类控制变量"
        if (size(col) == 0) return values
        if (method == "ffill") return contextby(ffill, values, code, time)
        if (method == "mean") {
            means = contextby(avg, values, time)
            return iif(isNull(values), means, values)
        }
        throw "不支持的回归 fill 方法"
    }
    """,
    dependencies=(IS_FINITE_NUMBER,),
)

FILL_REGRESSION_INPUTS = DolphinDBFunction(
    module="common",
    definition=r"""
    def fill_regression_inputs(target, controls, code, time, fill) {
        /*
        内部统一预填充，供面板批处理及公开单序列算符共用。

        Parameters
        ----------
        target : vector[NUMBER]
            原始数值目标；与 controls、code、time 等行数。
        controls : table
            有序的连续或分类控制列，不接受空解释变量表。
        code, time : vector
            当前节点参与行的证券和日期；调用方先应用 on 并保留原行位置。
        fill : string, dictionary or NULL
            ffill、mean、constant 规则或逐列配置；NULL 明确关闭，省略列默认 ffill。

        Returns
        -------
        filled : dictionary
            target 为填充目标向量，controls 为保持列顺序/分类类型的控制表。
            返回值与原参与行等长，不删除行，也不改变调用方的输入表或向量。

        Notes
        -----
        每列独立填充后再由回归计算共同有效掩码；不依赖其它列是否缺失。
        不缩短日期轴、不补区间外历史、不用未来数据，填充值正常计入 min_periods。
        公开单序列调用没有其他股票，mean 因而无法填补该日期唯一观测的缺失。

        Examples
        --------
        >>> fill_regression_inputs(1.0 NULL 3, table(1.0 2 NULL as x), take("A", 3), 1..3, "ffill").target
        [1, 1, 3]
        >>> fill_regression_inputs(1.0 NULL 3, table(1.0 2 NULL as x), take("A", 3), 1..3, "ffill").controls.x
        [1, 2, 2]
        */
        n = size(target)
        if (!is_vector_form(target) || !is_table_form(controls) || controls.rows() != n || controls.cols() == 0)
            throw "回归 target 和 controls 必须等长且解释变量非空"
        config = normalize_regression_fill(fill, controls.cols())
        if (!any(config.methods != "")) {
            fill_regression_column(target, "", NULL, code, time, true)
            for (name in controls.columnNames()) fill_regression_column(controls[name], "", NULL, code, time, false)
            return dict(`target`controls, [target, controls])
        }
        filled_target = fill_regression_column(target, config.methods[0], config.values[0], code, time, true)
        filled_controls = controls.copy()
        names = controls.columnNames()
        for (i in 0 : size(names)) {
            values = fill_regression_column(controls[names[i]], config.methods[i + 1], config.values[i + 1], code, time, false)
            replaceColumn!(filled_controls, symbol([names[i]])[0], values)
        }
        return dict(`target`controls, [filled_target, filled_controls])
    }
    """,
    dependencies=(NORMALIZE_REGRESSION_FILL, FILL_REGRESSION_COLUMN, IS_TABLE_FORM, IS_VECTOR_FORM),
)

ROLLING_BINARY_REGRESSION = DolphinDBFunction(
    module="common",
    definition=r"""
    def rolling_binary_regression(left, right, time, window, min_periods, method="ols", weights=NULL) {
        /* 单自变量同窗回归共用矩统计；接近退化或消去误差时才对原窗口做SVD。
         * WLS权重仅影响拟合，residual_std按所有共同有效行计算普通样本标准差。
         */
        n = size(left)
        if (size(right) != n || size(time) != n) throw "二元回归输入与time必须等长"
        result = table(take(double(NULL),n) as alpha, take(double(NULL),n) as beta0,
            take(double(NULL),n) as residual, take(double(NULL),n) as residual_std)
        if (n == 0) return result
        minimum = rolling_min_periods(window,min_periods)
        valid = is_finite_number(left) && is_finite_number(right)
        if (!any(valid)) return result
        origin_x = first(double(left[valid]))
        origin_y = first(double(right[valid]))
        x = iif(valid,double(left)-origin_x,double(NULL))
        y = iif(valid,double(right)-origin_y,double(NULL))
        calendar = type(window) == STRING
        if (calendar) {
            spans = calendar_window_spans(time,window)
            period = duration(normalize_calendar_window(window))
            dates = timestamp(time)
            counts = tmcount(dates,x,period)
            ux = tmavg(dates,x,period)
            uy = tmavg(dates,y,period)
            vx = tmvar(dates,x,period)
            vy = tmvar(dates,y,period)
            covariance = tmcovar(dates,x,y,period)
        } else {
            positions = 1..n
            spans = long(iif(positions>int(window),int(window),positions))
            if (int(window) == 1) return result
            counts = mcount(x,int(window),1)
            ux = mavg(x,int(window),1)
            uy = mavg(y,int(window),1)
            vx = mvar(x,int(window),1)
            vy = mvar(y,int(window),1)
            covariance = mcovar(x,y,int(window),1)
        }
        mx = ux
        my = uy
        variance = vx
        numerator = covariance
        reliable_moments = take(true,n)
        if (method == "wls") {
            mx = weighted_rolling_mean(x,time,window,minimum,weights)
            my = weighted_rolling_mean(y,time,window,minimum,weights)
            xx = weighted_rolling_mean(x*x,time,window,minimum,weights)
            xy = weighted_rolling_mean(x*y,time,window,minimum,weights)
            variance = xx-mx*mx
            numerator = xy-mx*my
            // 相减损失有效位时逐窗中心化拟合，不让错误但有限的系数通过快速路径。
            reliable_moments = variance > 1e-6*(abs(xx)+abs(mx*mx)) &&
                abs(numerator) > 1e-6*(abs(xy)+abs(mx*my))
            if (any(weights == 0)) reliable_moments = take(false,n)
        }
        beta = numerator/variance
        alpha = my-beta*mx
        residual_variance = vy+beta*beta*vx-2*beta*covariance
        magnitude = abs(vy)+abs(beta*beta*vx)+abs(2*beta*covariance)
        usable = counts>=max(2,minimum) && is_finite_number(beta) && variance>0
        stable = usable && reliable_moments && residual_variance>magnitude*1e-10
        result[`alpha] = iif(stable,origin_y+alpha-beta*origin_x,double(NULL))
        result[`beta0] = iif(stable,beta,double(NULL))
        result[`residual] = iif(stable,y-alpha-beta*x,double(NULL))
        result[`residual_std] = iif(stable,sqrt(residual_variance),double(NULL))
        // 恰好线性、零方差和较大的矩消去误差使用同一原窗口拟合，不把小负数强行截0。
        fallback = at(counts>=max(2,minimum) && !stable)
        for (i in fallback) {
            indices = (i-spans[i]+1)..i
            current_weights = NULL
            if (method == "wls") current_weights = double(weights[(size(weights)-size(indices)):size(weights)])
            fit = controls_regression(right[indices],table(left[indices] as x),true,method,current_weights,true)
            values = result.alpha
            values[i] = fit.alpha
            result[`alpha] = values
            if (size(fit.beta)>0) {
                values = result.beta0
                values[i] = fit.beta[0]
                result[`beta0] = values
            }
            values = result.residual
            values[i] = last(fit.residual)
            result[`residual] = values
            values = result.residual_std
            values[i] = fit.residual_std
            result[`residual_std] = values
        }
        return result
    }
    """,
    dependencies=(WEIGHTED_ROLLING_MEAN, CONTROLS_REGRESSION, CALENDAR_WINDOW_SPANS, ROLLING_MIN_PERIODS, IS_FINITE_NUMBER),
)

ROLLING_CONTROLS_REGRESSION = DolphinDBFunction(
    module="common",
    definition=r"""
    def rolling_controls_regression(target, controls, window, min_periods, intercept, time=NULL, method="ols", weights=NULL, binary=false) {
        /*
        内部滚动回归辅助函数，不登记为算符；四类标量输出共用每个窗口的同一次拟合。

        Parameters
        ----------
        target : vector[NUMBER]
            一只证券已按时间升序排列的目标序列。
        controls : table
            同行数的有序解释变量；允许连续、BOOL、STRING、SYMBOL，各窗口独立编码。
        window : int or string
            整数为右对齐的观测行数；字符串按 time 使用 (当前时间-window, 当前时间]。
            两者均包含当前行；缺失行占窗口位置，不向前凑样本，月和年不换算为固定天数。
        min_periods : int or NULL
            最少共同有效观测数；NULL 时整数窗口取 window，日历窗口取 1。
            不足时该窗口所有输出为 NULL，不要求先经过完整日历跨度。
        intercept : bool
            正常回归是否含截距；其余编码和退化规则与 controls_regression 相同。
        time : temporal vector or NULL, default NULL
            日历窗口必须提供等长、非 NULL、升序的时间向量；整数窗口不依赖该参数。
        method : string, default "ols"
            ols 为等权拟合；wls 使用显式窗口位置权重。
        weights : numeric vector or NULL
            WLS 从旧到新排列；整数窗口必须等长，日历窗口不得超过该权重长度。
            短窗口取末端权重，缺失值剔除前先按窗口位置对齐；0权重行保留残差，不重新配权。
        binary : bool, default false
            true 保留二元回归退化规则：少于两个配对或自变量无方差时为 NULL。

        Returns
        -------
        result : table
            内部使用的 alpha、residual、residual_std、beta0...数值列；每行对应原输入位置。
            residual 只取当前行残差；residual_std 为同一次拟合整组有效残差的 std(ddof=1)。

        Notes
        -----
        alpha/beta 可在当前行缺失但窗口仍有足够共同样本时有效；当前残差仍为 NULL。
        分类展开列顺序由当前窗口决定，无未来类别；该窗口不存在的系数位置为 NULL。
        不输出矩阵或数组因子，不将每次回归残差重新应用于以后的窗口。
        */
        if (!is_vector_form(target) || !is_table_form(controls) || controls.rows() != size(target) || controls.cols() == 0)
            throw "回归 target 和 controls 必须等长且解释变量非空"
        minimum = rolling_min_periods(window, min_periods)
        calendar = type(window) == STRING
        n = size(target)
        spans = long([])
        if (calendar) {
            if (!is_vector_form(time) || size(time) != n) throw "日历回归窗口必须传入等长time"
            spans = calendar_window_spans(time, window)
            if (minimum < 1) throw "min_periods必须为正整数"
        } else if (isNull(window) || window < 1 || window != int(window) || minimum < 1 || minimum > window)
            throw "滚动回归窗口参数无效"
        if (!(method in ["ols", "wls"])) throw "回归 method 必须为 ols 或 wls"
        if (method == "ols" && type(weights) != VOID) throw "OLS 不接受 weights"
        if (method == "wls") {
            if (!is_vector_form(weights) || size(weights) == 0) throw "WLS 必须提供非空 weights"
            if (!(type(weights) in [CHAR, SHORT, INT, LONG, FLOAT, DOUBLE])) throw "WLS weights 必须是数值"
            if (any(!is_finite_number(weights)) || any(weights < 0) || !any(weights > 0))
                throw "WLS weights 必须有限、非负且至少一项大于0"
            if (!calendar && size(weights) != int(window)) throw "WLS weights 长度必须等于 window"
            if (calendar && n > 0 && max(spans) > size(weights)) throw "日历窗口的观测数超过 weights 长度"
        }
        if (binary && (controls.cols() != 1 || !(type(controls[controls.columnNames()[0]]) in [CHAR, SHORT, INT, LONG, FLOAT, DOUBLE])))
            throw "二元回归必须有一个数值自变量"
        if (binary) {
            clock = time
            if (!calendar) clock = take(timestamp(0),n)
            return rolling_binary_regression(controls[controls.columnNames()[0]],target,clock,window,min_periods,method,weights)
        }
        output = dict(STRING, ANY)
        output["alpha"] = take(double(NULL), n)
        output["residual"] = take(double(NULL), n)
        output["residual_std"] = take(double(NULL), n)
        if (n == 0) return transpose(output)
        for (i in 0 .. (n - 1)) {
            if (calendar) first = i - spans[i] + 1
            else first = max(0, i - int(window) + 1)
            indices = first .. i
            current_weights = NULL
            if (method == "wls") current_weights = double(weights[(size(weights) - size(indices)):size(weights)])
            fit = controls_regression(target[indices], controls[indices], intercept, method, current_weights, binary)
            if (fit.nobs < minimum) continue
            values = output["alpha"]
            values[i] = fit.alpha
            output["alpha"] = values
            values = output["residual"]
            values[i] = last(fit.residual)
            output["residual"] = values
            values = output["residual_std"]
            values[i] = fit.residual_std
            output["residual_std"] = values
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
    dependencies=(CALENDAR_WINDOW_SPANS, ROLLING_MIN_PERIODS, ROLLING_BINARY_REGRESSION, CONTROLS_REGRESSION, IS_FINITE_NUMBER, IS_TABLE_FORM, IS_VECTOR_FORM),
)

CONTROLS_REGRESSION_BATCH = DolphinDBFunction(
    module="common",
    definition=r"""
    def controls_regression_batch(targets, controls, intercept, current_valid) {
        /*
        内部多目标回归辅助函数；只接收共同有效行和设计矩阵完全相同的一组目标。

        Parameters
        ----------
        targets : matrix[DOUBLE]
            行为共同有效观测，列为各股票目标；调用方已排除 NULL、NaN、Inf。
        controls : table
            与 targets 等行数的有序原始控制列；连续和分类编码规则同 controls_regression。
        intercept : bool
            正常拟合是否包含截距；无活动控制或小样本仍沿用去均值退化。
        current_valid : bool
            原窗口末行是否共同有效；false 时只返回系数，当天残差保持 NULL。

        Returns
        -------
        fit : dictionary
            alpha/residual 是按目标列排列的向量，beta 是展开控制列 × 目标列的矩阵。
            names 保留数值常量列位置；分类只使用本组当前窗口有效行并按升序删首类。
            residual_std 是同次拟合全部有效行残差的样本标准差向量，与当前行是否有效无关。

        Notes
        -----
        不合并不同有效掩码，不取全市场共同样本，不使用未来类别，不输出矩阵因子。
        每组只分解一次设计矩阵，pinv(X) ** targets 等价于各目标分别求最小范数解。
        当前行缺失时不把最后一个有效历史观测的残差冒充当天残差。
        无活动控制列、单样本或样本数不大于控制列数加截距项时，alpha 为各目标均值、
        beta 为 0；该退化规则也适用于 intercept=false。矩阵乘法可能有浮点舍入差异。

        Examples
        --------
        >>> controls_regression_batch(matrix(1.0 3 5 7, 2.0 5 8 11), table(0.0 1 2 3 as x), true, true).alpha
        [1, 2]
        >>> controls_regression_batch(matrix(1.0 3 5 7, 2.0 5 8 11), table(0.0 1 2 3 as x), true, true).beta
        [[2, 3]]
        >>> controls_regression_batch(matrix(1.0 3 5 7, 2.0 5 8 11), table(0.0 1 2 3 as x), true, false).residual
        [NULL, NULL]
        */
        n = targets.rows()
        count = targets.cols()
        names = array(STRING, 0)
        categories = array(STRING, 0)
        for (name in controls.columnNames()) {
            if (type(controls[name]) in [BOOL, SYMBOL, STRING]) {
                categories.append!(name)
                levels = sort(distinct(controls[name]))
                if (size(levels) > 1) {
                    for (j in 1 .. (size(levels) - 1))
                        names.append!(name + "_" + string(levels[j]))
                }
            } else names.append!(name)
        }
        encoded = controls
        if (size(categories) > 0) encoded = oneHot(controls, symbol(categories))
        active = array(STRING, 0)
        for (name in names) {
            if (!(name in encoded.columnNames())) throw "回归分类编码列不存在：" + name
            if (size(distinct(encoded[name])) > 1) active.append!(name)
        }
        beta = matrix(DOUBLE, size(names), count, count, 0.0)
        alpha = avg(targets)
        residual = flatten(targets[n - 1,]) - alpha
        window_residuals = targets.copy()
        for (column in 0 : count) window_residuals[column] = targets[column] - alpha[column]
        if (size(active) > 0 && n > 1 && n > size(active) + int(intercept)) {
            design = array(ANY, 0)
            if (intercept) design.append!(take(1.0, n))
            for (name in active) design.append!(double(encoded[name]))
            coefficients = pinv(matrix(design)) ** targets
            window_residuals = targets - matrix(design) ** coefficients
            alpha = take(0.0, count)
            if (intercept) alpha = flatten(coefficients[0,])
            fitted = alpha.copy()
            for (j in 0 .. (size(active) - 1)) {
                position = find(names, active[j])
                beta[position,] = coefficients[j + int(intercept),]
                fitted += flatten(coefficients[j + int(intercept),]) * double(last(encoded[active[j]]))
            }
            residual = flatten(targets[n - 1,]) - fitted
        }
        if (!current_valid) residual = take(double(NULL), count)
        fit = dict(STRING, ANY)
        fit["alpha"] = alpha
        fit["beta"] = beta
        fit["residual"] = residual
        fit["residual_std"] = std(window_residuals)
        fit["names"] = names
        return fit
    }
    """,
)

ROLLING_TRUE_COUNT = DolphinDBFunction(
    module="common",
    definition="""
    def rolling_true_count(value, window, min_periods) {
        // 将 NULL 按 false 处理，统计每个滚动窗口中的 true 数量。
        if (type(value) != BOOL) throw "条件型算符的 col 必须是 BOOL"
        if (window == 1) return int(nullFill(value, false))
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
