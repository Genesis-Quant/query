"""时序算符的 DolphinDB 实现。"""

from query.database.compile import DolphinDBFunction
from query.database.compile.common.functions import (
    DIVIDE_OR_NULL,
    MASK_EXPANDING_RESULT,
    MASK_PAIR_EXPANDING_RESULT,
    ROLLING_CONTROLS_REGRESSION,
    ROLLING_INTERCEPT,
    ROLLING_MIN_PERIODS,
    ROLLING_SLOPE,
    ROLLING_TRUE_COUNT,
    TALIB_MOVING_AVERAGE,
)

TS_CONTROLS_ROLLING_ALPHA = DolphinDBFunction(
    module="query",
    definition=r"""
    def ts_controls_rolling_alpha(target, controls, window, min_periods, intercept) {
        /*
        在右对齐多元滚动 OLS 中返回截距；函数独立接收原始目标和控制变量。

        Parameters
        ----------
        target : vector[NUMBER]
            一只证券按时间排序的数值因变量。
        controls : table
            同行数、有序的连续或分类变量；BOOL、STRING、SYMBOL 独热编码并删除首类。
        window : int
            当前观测及前 window-1 个观测，按行计数。
        min_periods : int or NULL
            最少共同有效样本，NULL 默认 window；缺失观测不跳位置。
        intercept : bool
            正常拟合是否含截距；退化窗口沿用 CS 的去均值规则。

        Returns
        -------
        result : vector[NUMBER]
            与目标等长的 DOUBLE 截距序列；历史不足、on=false 的恢复位置为 NULL。

        Notes
        -----
        目标、全部控制共同排除 NULL/非有限输入，分类基准仅取当前窗口的有效类别。
        alpha/beta 不代表整个窗口残差波动率；rolling_residual 只返回当前行残差。
        正常回归 intercept=false 时为 0；无有效控制列或小样本退化时为有效 target 均值。
        当前行缺失不影响此前有效样本参与拟合，达到 min_periods 仍可输出截距。

        Examples
        --------
        >>> ts_controls_rolling_alpha(1.0 3 5 7 9 11, table(0.0 1 2 3 4 5 as x), 4, 4, true)
        [NULL, NULL, NULL, 1, 1, 1]
        >>> ts_controls_rolling_alpha(1.0 2 4 8, table(take(1.0, 4) as constant), 2, 2, false)
        [NULL, 1.5, 3, 6]
        */
        return rolling_controls_regression(target, controls, window, min_periods, intercept).alpha
    }
    """,
    dependencies=(ROLLING_CONTROLS_REGRESSION,),
)

TS_CONTROLS_ROLLING_BETA = DolphinDBFunction(
    module="query",
    definition=r"""
    def ts_controls_rolling_beta(target, controls, window, min_periods, intercept, index) {
        /*
        在右对齐多元滚动 OLS 中返回指定解释变量系数；函数独立接收原始目标和控制变量。

        Parameters
        ----------
        target : vector[NUMBER]
            一只证券按时间排序的数值因变量。
        controls : table
            同行数、有序的连续或分类变量；BOOL、STRING、SYMBOL 独热编码并删除首类。
        window : int
            当前观测及前 window-1 个观测，按行计数。
        min_periods : int or NULL
            最少共同有效样本，NULL 默认 window；缺失观测不跳位置。
        intercept : bool
            正常拟合是否含截距；退化窗口沿用 CS 的去均值规则。
        index : int
            0 起算的当前窗口展开列位置，不包含截距；不存在时返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与目标等长的 DOUBLE 指定解释变量系数序列；历史不足、on=false 的恢复位置为 NULL。

        Notes
        -----
        目标、全部控制共同排除 NULL/非有限输入，分类基准仅取当前窗口的有效类别。
        alpha/beta 不代表整个窗口残差波动率；rolling_residual 只返回当前行残差。
        展开顺序先按 controls 列顺序，再按每列当前窗口有效类别升序删首类。
        数值常量列保留位置且系数为 0，分类只有一类时不占展开位置。
        不同窗口类别变化会改变索引对应的类别；没有该位置时为 NULL，不补 0。

        Examples
        --------
        >>> ts_controls_rolling_beta(1.0 3 5 7 9 11, table(0.0 1 2 3 4 5 as x), 4, 4, true, 0)
        [NULL, NULL, NULL, 2, 2, 2]
        >>> ts_controls_rolling_beta(1.0 3 5 7, table(0.0 1 2 3 as x), 4, 4, true, 1)
        [NULL, NULL, NULL, NULL]
        */
        if (isNull(index) || index < 0 || index != int(index)) throw "回归系数 index 必须是非负整数"
        coefficients = rolling_controls_regression(target, controls, window, min_periods, intercept)
        name = "beta" + string(int(index))
        if (!(name in coefficients.columnNames())) return take(double(NULL), size(target))
        return coefficients[name]
    }
    """,
    dependencies=(ROLLING_CONTROLS_REGRESSION,),
)

TS_CONTROLS_ROLLING_RESIDUAL = DolphinDBFunction(
    module="query",
    definition=r"""
    def ts_controls_rolling_residual(target, controls, window, min_periods, intercept) {
        /*
        在右对齐多元滚动 OLS 中返回当前观测残差；函数独立接收原始目标和控制变量。

        Parameters
        ----------
        target : vector[NUMBER]
            一只证券按时间排序的数值因变量。
        controls : table
            同行数、有序的连续或分类变量；BOOL、STRING、SYMBOL 独热编码并删除首类。
        window : int
            当前观测及前 window-1 个观测，按行计数。
        min_periods : int or NULL
            最少共同有效样本，NULL 默认 window；缺失观测不跳位置。
        intercept : bool
            正常拟合是否含截距；退化窗口沿用 CS 的去均值规则。

        Returns
        -------
        result : vector[NUMBER]
            与目标等长的 DOUBLE 当前观测残差序列；历史不足、on=false 的恢复位置为 NULL。

        Notes
        -----
        目标、全部控制共同排除 NULL/非有限输入，分类基准仅取当前窗口的有效类别。
        alpha/beta 不代表整个窗口残差波动率；rolling_residual 只返回当前行残差。
        当前目标或任一控制缺失时，当天残差为 NULL；不能以前一天残差填补。
        窗口无有效控制或样本不足时沿用去均值退化，当天输出 y_t-avg(y)。
        后续 rolling_std/rolling_mean 统计的是逐日各自拟合的残差序列，
        不是把当天系数应用于当前窗口全部历史观测后重新计算的同窗残差统计。

        Examples
        --------
        >>> ts_controls_rolling_residual(1.0 3 5 7 9 11, table(0.0 1 2 3 4 5 as x), 4, 4, true)
        [NULL, NULL, NULL, 0, 0, 0]
        >>> ts_controls_rolling_residual(1.0 2 4 8, table(take(1.0, 4) as constant), 2, 2, true)
        [NULL, 0.5, 1, 2]
        */
        return rolling_controls_regression(target, controls, window, min_periods, intercept).residual
    }
    """,
    dependencies=(ROLLING_CONTROLS_REGRESSION,),
)

TS_BINARY_CROSS_ABOVE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_cross_above(left, right) {
        /*
        标记 left 从不高于 right 变为高于 right 的位置。

        只有发生穿越的当前位置返回 true；首个位置以及未发生穿越的位置返回 false。

        Parameters
        ----------
        left : vector
            需要检测交叉的主序列。
        right : vector
            用于比较的基准或阈值序列。

        Returns
        -------
        result : vector[BOOL]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：当前或前一期任一输入为 NULL 时，交叉条件不成立并返回 false；输出不传播 NULL。

        边界语义：首行没有前一期，因此返回 false。只有从非目标侧跨到目标侧才返回
        true，连续停留在目标侧不会重复触发。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5
        >>> ts_binary_cross_above(left, right)
        [false, true, false, true, false, true, false, true]

        缺失的当前值或前值不会触发交叉：
        >>> ts_binary_cross_above(double([1, NULL, 3, 5]), double([2, 2, 2, NULL]))
        [false, false, true, false]
        */
        previous_left = move(left, 1)
        previous_right = move(right, 1)
        valid = isValid(left) && isValid(right) && isValid(previous_left) && isValid(previous_right)
        return valid && (left > right) && (previous_left <= previous_right)
    }
    """
)

TS_BINARY_CROSS_BELOW = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_cross_below(left, right) {
        /*
        标记 left 从不低于 right 变为低于 right 的位置。

        只有发生穿越的当前位置返回 true；首个位置以及未发生穿越的位置返回 false。

        Parameters
        ----------
        left : vector
            需要检测交叉的主序列。
        right : vector
            用于比较的基准或阈值序列。

        Returns
        -------
        result : vector[BOOL]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：当前或前一期任一输入为 NULL 时，交叉条件不成立并返回 false；输出不传播 NULL。

        边界语义：首行没有前一期，因此返回 false。只有从非目标侧跨到目标侧才返回
        true，连续停留在目标侧不会重复触发。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5
        >>> ts_binary_cross_below(left, right)
        [true, false, true, false, true, false, true, false]

        缺失的当前值或前值不会触发交叉：
        >>> ts_binary_cross_below(double([1, NULL, 3, 5]), double([2, 2, 2, NULL]))
        [false, false, false, false]
        */
        previous_left = move(left, 1)
        previous_right = move(right, 1)
        valid = isValid(left) && isValid(right) && isValid(previous_left) && isValid(previous_right)
        return valid && (left < right) && (previous_left >= previous_right)
    }
    """
)

TS_BINARY_EWM_CORR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_ewm_corr(left, right, com, span, half_life, alpha, min_periods, adjust, ignore_na, bias) {
        /*
        计算两个序列的指数加权移动相关系数。

        com、span、half_life 和 alpha 必须且只能提供一个，它们最终确定同一个平滑系数。结果与输入等长，并从序列起点递推或按完整权重计算。

        min_periods 控制首个非 NULL 结果所需的有效观测数；adjust 控制归一化权重形式；ignore_na 控制 NULL 是否占用权重位置。

        Parameters
        ----------
        left : vector
            第一条按时间升序排列的数值序列。
        right : vector
            与 left 等长的第二条数值序列。
        com : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 1 / (1 + com)，com >= 0。
        span : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 2 / (span + 1)，span >= 1。
        half_life : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 1 - exp(log(0.5) / half_life)，half_life > 0。
        alpha : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。直接指定平滑系数，0 < alpha <= 1。
        min_periods : int, default 0
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。
        adjust : bool, default true
            true 时使用显式衰减权重并除以权重和；false 时使用递归更新形式。
        ignore_na : bool, default false
            false 时权重按绝对位置计算，NULL 仍占用位置；true 时权重只按有效观测的相对位置计算。
        bias : bool, default false
            true 使用有偏估计；false 对有限样本进行无偏修正。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Raises
        ------
        DolphinDB exception
            未提供任何 EWM 衰减参数时抛出异常。正常 DSL 构造会在 Python 校验阶段阻止该输入。

        Notes
        -----
        NULL 处理：输入 NULL 不会被填充。ignore_na=false
        时缺失位置仍影响后续权重距离，ignore_na=true 时仅按有效观测的相对位置累计权重；min_periods
        统计非 NULL 观测。

        衰减与边界：com、span、half_life、alpha 必须且只能提供一个。只使用 left 与 right
        同时有效的配对观测；bias 控制协方差估计口径，有效配对不足或尺度为 0 时返回 NULL。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5

        使用 com 指定衰减：
        >>> ts_binary_ewm_corr(left, right, 1.0, double(NULL), double(NULL), double(NULL), 1, true, false, false)
        [NULL, 1, 0.423659, 0.873422, 0.615603, 0.846314, 0.753962, 0.872929]

        使用 span 指定衰减：
        >>> ts_binary_ewm_corr(left, right, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, false)
        [NULL, 1, 0.423659, 0.873422, 0.615603, 0.846314, 0.753962, 0.872929]

        使用 half_life 指定衰减：
        >>> ts_binary_ewm_corr(left, right, double(NULL), double(NULL), 2.0, double(NULL), 1, true, false, false)
        [NULL, 1, 0.554361, 0.874701, 0.735609, 0.877794, 0.855495, 0.911043]

        使用 alpha 指定衰减：
        >>> ts_binary_ewm_corr(left, right, double(NULL), double(NULL), double(NULL), 0.5, 1, true, false, false)
        [NULL, 1, 0.423659, 0.873422, 0.615603, 0.846314, 0.753962, 0.872929]

        adjust=false 使用递归形式：
        >>> ts_binary_ewm_corr(left, right, double(NULL), 3.0, double(NULL), double(NULL), 1, false, false, false)
        [NULL, 1, 0.622543, 0.89912, 0.68492, 0.86651, 0.782492, 0.881802]

        min_periods=3 延后首个有效结果：
        >>> ts_binary_ewm_corr(left, right, double(NULL), 3.0, double(NULL), double(NULL), 3, true, false, false)
        [NULL, NULL, 0.423659, 0.873422, 0.615603, 0.846314, 0.753962, 0.872929]

        bias=false 使用无偏估计：
        >>> ts_binary_ewm_corr(left, right, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, false)
        [NULL, 1, 0.423659, 0.873422, 0.615603, 0.846314, 0.753962, 0.872929]

        bias=true 使用有偏估计：
        >>> ts_binary_ewm_corr(left, right, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, true)
        [NULL, 1, 0.423659, 0.873422, 0.615603, 0.846314, 0.753962, 0.872929]
        */
        if (!isNull(com)) return ewmCorr(left, com, , , , int(min_periods), adjust, ignore_na, right, bias)
        if (!isNull(span)) return ewmCorr(left, , span, , , int(min_periods), adjust, ignore_na, right, bias)
        if (!isNull(half_life)) return ewmCorr(left, , , half_life, , int(min_periods), adjust, ignore_na, right, bias)
        if (!isNull(alpha)) return ewmCorr(left, , , , alpha, int(min_periods), adjust, ignore_na, right, bias)
        throw "EWM 必须提供一个衰减参数"
    }
    """
)

TS_BINARY_EWM_COV = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_ewm_cov(left, right, com, span, half_life, alpha, min_periods, adjust, ignore_na, bias) {
        /*
        计算两个序列的指数加权移动协方差。

        com、span、half_life 和 alpha 必须且只能提供一个，它们最终确定同一个平滑系数。结果与输入等长，并从序列起点递推或按完整权重计算。

        min_periods 控制首个非 NULL 结果所需的有效观测数；adjust 控制归一化权重形式；ignore_na 控制 NULL 是否占用权重位置。

        Parameters
        ----------
        left : vector
            第一条按时间升序排列的数值序列。
        right : vector
            与 left 等长的第二条数值序列。
        com : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 1 / (1 + com)，com >= 0。
        span : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 2 / (span + 1)，span >= 1。
        half_life : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 1 - exp(log(0.5) / half_life)，half_life > 0。
        alpha : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。直接指定平滑系数，0 < alpha <= 1。
        min_periods : int, default 0
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。
        adjust : bool, default true
            true 时使用显式衰减权重并除以权重和；false 时使用递归更新形式。
        ignore_na : bool, default false
            false 时权重按绝对位置计算，NULL 仍占用位置；true 时权重只按有效观测的相对位置计算。
        bias : bool, default false
            true 使用有偏估计；false 对有限样本进行无偏修正。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Raises
        ------
        DolphinDB exception
            未提供任何 EWM 衰减参数时抛出异常。正常 DSL 构造会在 Python 校验阶段阻止该输入。

        Notes
        -----
        NULL 处理：输入 NULL 不会被填充。ignore_na=false
        时缺失位置仍影响后续权重距离，ignore_na=true 时仅按有效观测的相对位置累计权重；min_periods
        统计非 NULL 观测。

        衰减与边界：com、span、half_life、alpha 必须且只能提供一个。只使用 left 与 right
        同时有效的配对观测；bias 控制协方差估计口径，有效配对不足或尺度为 0 时返回 NULL。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5

        使用 com 指定衰减：
        >>> ts_binary_ewm_cov(left, right, 1.0, double(NULL), double(NULL), double(NULL), 1, true, false, false)
        [NULL, 0.375, 0.125, 0.682143, 0.547581, 1.02131, 0.640748, 0.966084]

        使用 span 指定衰减：
        >>> ts_binary_ewm_cov(left, right, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, false)
        [NULL, 0.375, 0.125, 0.682143, 0.547581, 1.02131, 0.640748, 0.966084]

        使用 half_life 指定衰减：
        >>> ts_binary_ewm_cov(left, right, double(NULL), double(NULL), 2.0, double(NULL), 1, true, false, false)
        [NULL, 0.375, 0.188506, 0.713863, 0.790331, 1.35732, 1.24005, 1.6724]

        使用 alpha 指定衰减：
        >>> ts_binary_ewm_cov(left, right, double(NULL), double(NULL), double(NULL), 0.5, 1, true, false, false)
        [NULL, 0.375, 0.125, 0.682143, 0.547581, 1.02131, 0.640748, 0.966084]

        adjust=false 使用递归形式：
        >>> ts_binary_ewm_cov(left, right, double(NULL), 3.0, double(NULL), double(NULL), 1, false, false, false)
        [NULL, 0.375, 0.225, 0.815476, 0.707353, 1.16752, 0.745879, 1.04342]

        min_periods=3 延后首个有效结果：
        >>> ts_binary_ewm_cov(left, right, double(NULL), 3.0, double(NULL), double(NULL), 3, true, false, false)
        [NULL, NULL, 0.125, 0.682143, 0.547581, 1.02131, 0.640748, 0.966084]

        bias=false 使用无偏估计：
        >>> ts_binary_ewm_cov(left, right, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, false)
        [NULL, 0.375, 0.125, 0.682143, 0.547581, 1.02131, 0.640748, 0.966084]

        bias=true 使用有偏估计：
        >>> ts_binary_ewm_cov(left, right, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, true)
        [0, 0.166667, 0.0714286, 0.424444, 0.353278, 0.670068, 0.423802, 0.64153]
        */
        if (!isNull(com)) return ewmCov(left, com, , , , int(min_periods), adjust, ignore_na, right, bias)
        if (!isNull(span)) return ewmCov(left, , span, , , int(min_periods), adjust, ignore_na, right, bias)
        if (!isNull(half_life)) return ewmCov(left, , , half_life, , int(min_periods), adjust, ignore_na, right, bias)
        if (!isNull(alpha)) return ewmCov(left, , , , alpha, int(min_periods), adjust, ignore_na, right, bias)
        throw "EWM 必须提供一个衰减参数"
    }
    """
)

TS_BINARY_EXPANDING_BETA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_expanding_beta(left, right, min_periods) {
        /*
        计算截至当前位置以 left 解释 right 的扩展回归斜率。

        第 i 个结果使用从序列首个观测到第 i 个观测的全部历史。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        left : vector
            回归中的解释变量向量。
        right : vector
            回归中的因变量向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：协方差、相关系数和 beta 只使用两侧同时有效的观测；有效配对不足时结果为 NULL。

        扩展窗口：二元统计始终使用截至当前位置的累计有效配对，不单独填充任一侧。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5

        min_periods=1：
        >>> ts_binary_expanding_beta(left, right, 1)
        [NULL, 0.333333, 0.428571, 0.453333, 0.649123, 0.714286, 0.818966, 0.819512]

        min_periods=3：
        >>> ts_binary_expanding_beta(left, right, 3)
        [NULL, NULL, 0.428571, 0.453333, 0.649123, 0.714286, 0.818966, 0.819512]

        min_periods=5：
        >>> ts_binary_expanding_beta(left, right, 5)
        [NULL, NULL, NULL, NULL, 0.649123, 0.714286, 0.818966, 0.819512]
        */
        result = cumbeta(right, left)
        return mask_pair_expanding_result(result, left, right, min_periods)
    }
    """,
    dependencies=(MASK_PAIR_EXPANDING_RESULT,)
)

TS_BINARY_EXPANDING_CORR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_expanding_corr(left, right, min_periods) {
        /*
        计算截至当前位置两个序列的扩展 Pearson 相关系数。

        第 i 个结果使用从序列首个观测到第 i 个观测的全部历史。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        left : vector
            第一条按时间升序排列的数值序列。
        right : vector
            与 left 等长的第二条数值序列。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：协方差、相关系数和 beta 只使用两侧同时有效的观测；有效配对不足时结果为 NULL。

        扩展窗口：二元统计始终使用截至当前位置的累计有效配对，不单独填充任一侧。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5

        min_periods=1：
        >>> ts_binary_expanding_corr(left, right, 1)
        [NULL, 1, 0.654654, 0.877876, 0.805682, 0.893633, 0.894054, 0.927625]

        min_periods=3：
        >>> ts_binary_expanding_corr(left, right, 3)
        [NULL, NULL, 0.654654, 0.877876, 0.805682, 0.893633, 0.894054, 0.927625]

        min_periods=5：
        >>> ts_binary_expanding_corr(left, right, 5)
        [NULL, NULL, NULL, NULL, 0.805682, 0.893633, 0.894054, 0.927625]
        */
        result = cumcorr(left, right)
        return mask_pair_expanding_result(result, left, right, min_periods)
    }
    """,
    dependencies=(MASK_PAIR_EXPANDING_RESULT,)
)

TS_BINARY_EXPANDING_COV = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_expanding_cov(left, right, min_periods) {
        /*
        计算截至当前位置两个序列的扩展样本协方差。

        第 i 个结果使用从序列首个观测到第 i 个观测的全部历史。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        left : vector
            第一条按时间升序排列的数值序列。
        right : vector
            与 left 等长的第二条数值序列。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：协方差、相关系数和 beta 只使用两侧同时有效的观测；有效配对不足时结果为 NULL。

        扩展窗口：二元统计始终使用截至当前位置的累计有效配对，不单独填充任一侧。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5

        min_periods=1：
        >>> ts_binary_expanding_cov(left, right, 1)
        [NULL, 0.375, 0.25, 0.708333, 0.925, 1.5, 1.69643, 2.25]

        min_periods=3：
        >>> ts_binary_expanding_cov(left, right, 3)
        [NULL, NULL, 0.25, 0.708333, 0.925, 1.5, 1.69643, 2.25]

        min_periods=5：
        >>> ts_binary_expanding_cov(left, right, 5)
        [NULL, NULL, NULL, NULL, 0.925, 1.5, 1.69643, 2.25]
        */
        result = cumcovar(left, right)
        return mask_pair_expanding_result(result, left, right, min_periods)
    }
    """,
    dependencies=(MASK_PAIR_EXPANDING_RESULT,)
)

TS_BINARY_ROLLING_ALPHA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_rolling_alpha(left, right, window, min_periods) {
        /*
        计算滚动窗口内以 left 解释 right 的回归截距。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        回归方向固定为 right 对 left；left 是解释变量，right 是因变量。

        Parameters
        ----------
        left : vector
            回归中的解释变量向量。
        right : vector
            回归中的因变量向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：二元窗口统计只使用两侧同时有效的观测；有效配对不足、解释变量零方差或当前位置无法形成残差时返回
        NULL。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5

        min_periods=NULL 时要求完整窗口：
        >>> ts_binary_rolling_alpha(left, right, 3, int(NULL))
        [NULL, NULL, 1.21429, 1.51923, 1.82692, 1.75, 2.64286, 2.78571]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_binary_rolling_alpha(left, right, 3, 1)
        [NULL, 1.16667, 1.21429, 1.51923, 1.82692, 1.75, 2.64286, 2.78571]

        min_periods=2：
        >>> ts_binary_rolling_alpha(left, right, 3, 2)
        [NULL, 1.16667, 1.21429, 1.51923, 1.82692, 1.75, 2.64286, 2.78571]

        扩大到 4 期窗口：
        >>> ts_binary_rolling_alpha(left, right, 4, 2)
        [NULL, 1.16667, 1.21429, 1.17333, 1.075, 1.37333, 1.15, 2.19231]
        */
        minimum = rolling_min_periods(window, min_periods)
        return rolling_intercept(left, right, window, minimum)
    }
    """,
    dependencies=(ROLLING_INTERCEPT, ROLLING_MIN_PERIODS)
)

TS_BINARY_ROLLING_BETA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_rolling_beta(left, right, window, min_periods) {
        /*
        计算滚动窗口内以 left 解释 right 的回归斜率。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        回归方向固定为 right 对 left；left 是解释变量，right 是因变量。

        Parameters
        ----------
        left : vector
            回归中的解释变量向量。
        right : vector
            回归中的因变量向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：二元窗口统计只使用两侧同时有效的观测；有效配对不足、解释变量零方差或当前位置无法形成残差时返回
        NULL。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5

        min_periods=NULL 时要求完整窗口：
        >>> ts_binary_rolling_beta(left, right, 3, int(NULL))
        [NULL, NULL, 0.428571, 0.346154, 0.423077, 0.5, 0.428571, 0.428571]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_binary_rolling_beta(left, right, 3, 1)
        [NULL, 0.333333, 0.428571, 0.346154, 0.423077, 0.5, 0.428571, 0.428571]

        min_periods=2：
        >>> ts_binary_rolling_beta(left, right, 3, 2)
        [NULL, 0.333333, 0.428571, 0.346154, 0.423077, 0.5, 0.428571, 0.428571]

        扩大到 4 期窗口：
        >>> ts_binary_rolling_beta(left, right, 4, 2)
        [NULL, 0.333333, 0.428571, 0.453333, 0.6, 0.586667, 0.7, 0.538462]
        */
        minimum = rolling_min_periods(window, min_periods)
        return rolling_slope(left, right, window, minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS, ROLLING_SLOPE)
)

TS_BINARY_ROLLING_CORR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_rolling_corr(left, right, window, min_periods) {
        /*
        计算两个序列的滚动 Pearson 相关系数。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        left : vector
            第一条按时间升序排列的数值序列。
        right : vector
            与 left 等长的第二条数值序列。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：二元窗口统计只使用两侧同时有效的观测；有效配对不足、解释变量零方差或当前位置无法形成残差时返回
        NULL。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5

        min_periods=NULL 时要求完整窗口：
        >>> ts_binary_rolling_corr(left, right, 3, int(NULL))
        [NULL, NULL, 0.654654, 0.720577, 0.576557, 0.5, 0.654654, 0.654654]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_binary_rolling_corr(left, right, 3, 1)
        [NULL, 1, 0.654654, 0.720577, 0.576557, 0.5, 0.654654, 0.654654]

        min_periods=2：
        >>> ts_binary_rolling_corr(left, right, 3, 2)
        [NULL, 1, 0.654654, 0.720577, 0.576557, 0.5, 0.654654, 0.654654]

        扩大到 4 期窗口：
        >>> ts_binary_rolling_corr(left, right, 4, 2)
        [NULL, 1, 0.654654, 0.877876, 0.641427, 0.803326, 0.52915, 0.868243]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mcorr(left, right, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_BINARY_ROLLING_COV = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_rolling_cov(left, right, window, min_periods) {
        /*
        计算两个序列的滚动样本协方差。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        left : vector
            第一条按时间升序排列的数值序列。
        right : vector
            与 left 等长的第二条数值序列。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：二元窗口统计只使用两侧同时有效的观测；有效配对不足、解释变量零方差或当前位置无法形成残差时返回
        NULL。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5

        min_periods=NULL 时要求完整窗口：
        >>> ts_binary_rolling_cov(left, right, 3, int(NULL))
        [NULL, NULL, 0.25, 0.375, 0.458333, 0.291667, 0.25, 0.25]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_binary_rolling_cov(left, right, 3, 1)
        [NULL, 0.375, 0.25, 0.375, 0.458333, 0.291667, 0.25, 0.25]

        min_periods=2：
        >>> ts_binary_rolling_cov(left, right, 3, 2)
        [NULL, 0.375, 0.25, 0.375, 0.458333, 0.291667, 0.25, 0.25]

        扩大到 4 期窗口：
        >>> ts_binary_rolling_cov(left, right, 4, 2)
        [NULL, 0.375, 0.25, 0.708333, 0.5, 0.916667, 0.291667, 0.583333]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mcovar(left, right, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_BINARY_ROLLING_RESIDUAL = DolphinDBFunction(
    module="query",
    definition="""
    def ts_binary_rolling_residual(left, right, window, min_periods) {
        /*
        返回滚动窗口内以 left 解释 right 的当前观测残差。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        回归方向固定为 right 对 left；left 是解释变量，right 是因变量。

        Parameters
        ----------
        left : vector
            回归中的解释变量向量。
        right : vector
            回归中的因变量向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：二元窗口统计只使用两侧同时有效的观测；有效配对不足、解释变量零方差或当前位置无法形成残差时返回
        NULL。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> left = 1.0 2.5 2.0 4.0 3.5 5.0 4.5 6.0
        >>> right = 1.5 2.0 2.5 3.0 4.0 4.5 5.0 5.5

        min_periods=NULL 时要求完整窗口：
        >>> ts_binary_rolling_residual(left, right, 3, int(NULL))
        [NULL, NULL, 0.428571, 0.0961538, 0.692308, 0.25, 0.428571, 0.142857]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_binary_rolling_residual(left, right, 3, 1)
        [NULL, 0, 0.428571, 0.0961538, 0.692308, 0.25, 0.428571, 0.142857]

        min_periods=2：
        >>> ts_binary_rolling_residual(left, right, 3, 2)
        [NULL, 0, 0.428571, 0.0961538, 0.692308, 0.25, 0.428571, 0.142857]

        扩大到 4 期窗口：
        >>> ts_binary_rolling_residual(left, right, 4, 2)
        [NULL, 0, 0.428571, 0.0133333, 0.825, 0.193333, 0.7, 0.0769231]
        */
        minimum = rolling_min_periods(window, min_periods)
        slope = rolling_slope(left, right, window, minimum)
        intercept = rolling_intercept(left, right, window, minimum)
        return right - intercept - slope * left
    }
    """,
    dependencies=(ROLLING_INTERCEPT, ROLLING_MIN_PERIODS, ROLLING_SLOPE)
)

TS_TALIB_AD = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_ad(high, low, close, volume) {
        /*
        计算 TA-Lib AD（累积/派发线）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        volume : vector
            成交量向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充，而是原样交给 TA 状态函数；缺失行可能保持上一累计状态，而不保证在同位置返回
        NULL。需要完整输入时应通过 on 显式排除不完整行。

        计算定义：按资金流乘数 ((close-low)-(high-close))/(high-low) 乘
        volume，并对资金流量累计求和。

        状态边界：这是累计状态指标，不需要固定窗口预热；当前输出可能依赖此前全部观测，因此中间缺失值的影响可能延续到后续位置
        。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5
        >>> volume = long(1000 1200 900 1300 1400 1100 1500 1600 1250 1700 1800 1550)
        >>> tail(ts_talib_ad(high, low, close, volume), 3)
        [-1177.27, -1340.91, -1481.82]

        NULL 输入示例：
        >>> high=double([2,3,NULL]); low=double([0,1,1]); close=double([1,2,2]); volume=long([10,20,30])
        >>> ts_talib_ad(high, low, close, volume)
        [0, 0, 0]
        */
        return ta::ad(high, low, close, volume)
    }
    """
)

TS_TALIB_ADX = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_adx(high, low, close, time_period) {
        /*
        计算 TA-Lib ADX（平均趋向指数）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：由平滑后的正负方向指标计算趋势强度，通常位于 0 到 100；数值不表示趋势方向。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_adx(high, low, close, 2), 3)
        [49.2087, 63.2205, 38.691]

        time_period=3：
        >>> tail(ts_talib_adx(high, low, close, 3), 3)
        [54.5529, 59.3433, 50.4964]

        time_period=5：
        >>> tail(ts_talib_adx(high, low, close, 5), 3)
        [53.4264, 55.3231, 52.8917]
        */
        return ta::adx(high, low, close, int(time_period))
    }
    """
)

TS_TALIB_ADXR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_adxr(high, low, close, time_period) {
        /*
        计算 TA-Lib ADXR（平均趋向指数评级）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：把当前 ADX 与滞后一个 time_period 的 ADX 取平均，用于进一步平滑趋势强度。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_adxr(high, low, close, 2), 3)
        [43.2511, 56.2146, 50.9558]

        time_period=3：
        >>> tail(ts_talib_adxr(high, low, close, 3), 3)
        [60.4019, 56.2579, 52.5246]

        time_period=5：
        >>> tail(ts_talib_adxr(high, low, close, 5), 3)
        [NULL, NULL, NULL]
        */
        return ta::adxr(high, low, close, int(time_period))
    }
    """
)

TS_TALIB_APO = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_apo(col, fast_period, slow_period, ma_type) {
        /*
        计算 TA-Lib APO（绝对价格振荡器）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        fast_period : int, default 12
            快线周期，必须小于 slow_period。
        slow_period : int, default 26
            慢线周期，必须大于 fast_period。
        ma_type : int, default 0
            TA-Lib 移动平均类型编号：0=SMA、1=EMA、2=WMA、3=DEMA、4=TEMA、5=TRIMA、6=KAMA、8=T3。
            当前 DolphinDB 后端不支持 7=MAMA，模型会在构造阶段拒绝；T3 使用 TA-Lib 标准的 0.7 成交量因子。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：以指定 ma_type 计算快慢移动平均，并返回快线减慢线的绝对价格振荡值。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        2/4 周期的简单移动平均：
        >>> tail(ts_talib_apo(close, 2, 4, 0), 3)
        [0.075, 0.25, 0.225]

        3/6 周期的简单移动平均：
        >>> tail(ts_talib_apo(close, 3, 6, 0), 3)
        [0.316667, 0.283333, 0.283333]

        2/4 周期的指数移动平均：
        >>> tail(ts_talib_apo(close, 2, 4, 1), 3)
        [0.207297, 0.245492, 0.134333]

        2/4 周期的加权移动平均：
        >>> tail(ts_talib_apo(close, 2, 4, 2), 3)
        [0.0833333, 0.2, 0.0866667]
        */
        fast = talib_moving_average(col, fast_period, ma_type)
        slow = talib_moving_average(col, slow_period, ma_type)
        return fast - slow
    }
    """,
    dependencies=(TALIB_MOVING_AVERAGE,),
)

TS_TALIB_AROON = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_aroon(high, low, time_period, output) {
        /*
        计算 TA-Lib AROON（Aroon 上升线或下降线）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        底层指标产生多个向量，output 只选择其中一个返回。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。
        output : {"down", "up"}, default "up"
            每次调用只返回一个输出向量：
            * "down"：Aroon 下降线。
            * "up"：Aroon 上升线。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：根据 time_period 内距最近最高价和最低价的期数，分别得到 0 到 100 的 Aroon
        Up/Down。

        预热与输出：满足回看周期前返回前置 NULL；函数只返回 output
        指定的分量，选择分量不会改变底层多输出指标的计算。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        返回 output="down"：
        >>> tail(ts_talib_aroon(high, low, 3, "down"), 3)
        [0, 33.3333, 0]

        返回 output="up"：
        >>> tail(ts_talib_aroon(high, low, 3, "up"), 3)
        [100, 100, 66.6667]

        两期下降线：
        >>> tail(ts_talib_aroon(high, low, 2, "down"), 3)
        [50, 0, 0]

        两期上升线：
        >>> tail(ts_talib_aroon(high, low, 2, "up"), 3)
        [100, 100, 50]

        五期下降线：
        >>> tail(ts_talib_aroon(high, low, 5, "down"), 3)
        [20, 0, 0]

        五期上升线：
        >>> tail(ts_talib_aroon(high, low, 5, "up"), 3)
        [100, 100, 80]
        */
        values = ta::aroon(high, low, int(time_period))
        if (output == "down") return values[0]
        return values[1]
    }
    """
)

TS_TALIB_AROONOSC = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_aroonOsc(high, low, time_period) {
        /*
        计算 TA-Lib AROONOSC（Aroon 振荡器）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：返回 Aroon Up 减 Aroon Down，用正负号表达上涨或下跌趋势占优。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_aroonOsc(high, low, 2), 3)
        [50, 100, 50]

        time_period=3：
        >>> tail(ts_talib_aroonOsc(high, low, 3), 3)
        [100, 66.6667, 66.6667]

        time_period=5：
        >>> tail(ts_talib_aroonOsc(high, low, 5), 3)
        [80, 100, 80]
        */
        result = ta::aroonOsc(high, low, int(time_period))
        valid = isValid(high) && isValid(low)
        first = ifirstNot(iif(valid, 1, int(NULL)))
        if (first < 0) return result
        positions = 0..(size(result) - 1)
        return iif(positions < first + int(time_period), double(NULL), result)
    }
    """
)

TS_TALIB_ATR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_atr(high, low, close, time_period) {
        /*
        计算 TA-Lib ATR（平均真实波幅）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        time_period : int
            技术指标观察周期，必须为至少 2 的整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：先计算真实波幅 max(high-low, abs(high-prevClose),
        abs(low-prevClose))，再做 Wilder 平滑。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_atr(high, low, close, 2), 3)
        [1.10078, 1.10039, 1.1002]

        time_period=3：
        >>> tail(ts_talib_atr(high, low, close, 3), 3)
        [1.10293, 1.10195, 1.1013]

        time_period=5：
        >>> tail(ts_talib_atr(high, low, close, 5), 3)
        [1.10819, 1.10655, 1.10524]
        */
        return ta::atr(high, low, close, int(time_period))
    }
    """
)

TS_TALIB_AVGPRICE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_avgPrice(open, high, low, close) {
        /*
        计算 TA-Lib AVGPRICE（平均价格）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        open : vector
            开盘价向量。
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：每行所需的任一价格输入为 NULL 时，该行结果为 NULL；函数不前向填充 OHLC 输入。

        计算定义：逐行计算 (open + high + low + close) / 4。

        输出边界：这是逐行价格变换，不需要预热期；结果与输入等长，数值公式由 ta::avgPrice 定义。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> open = close - 0.1
        >>> high = close + 0.6
        >>> low = close - 0.5
        >>> tail(ts_talib_avgPrice(open, high, low, close), 3)
        [12, 12.3, 12.1]

        NULL 输入示例：
        >>> open=double([1,NULL]); high=double([2,3]); low=double([0,1]); close=double([1,2])
        >>> ts_talib_avgPrice(open, high, low, close)
        [1, NULL]
        */
        return ta::avgPrice(open, high, low, close)
    }
    """
)

TS_TALIB_BBANDS = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_bBands(col, time_period, nbdev_up, nbdev_down, ma_type, output) {
        /*
        计算 TA-Lib BBANDS（布林带）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        底层指标产生多个向量，output 只选择其中一个返回。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。
        nbdev_up : float, default 2.0
            布林带上轨相对中轨的标准差倍数。
        nbdev_down : float, default 2.0
            布林带下轨相对中轨的标准差倍数。
        ma_type : int, default 0
            TA-Lib 移动平均类型编号：0=SMA、1=EMA、2=WMA、3=DEMA、4=TEMA、5=TRIMA、6=KAMA、8=T3。
            当前 DolphinDB 后端不支持 7=MAMA，模型会在构造阶段拒绝；T3 使用 TA-Lib 标准的 0.7 成交量因子。
        output : {"upper", "middle", "lower"}, default "middle"
            每次调用只返回一个输出向量：
            * "upper"：上轨。
            * "middle"：中轨移动平均。
            * "lower"：下轨。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：middle 为指定类型的移动平均，upper/lower 为 middle 加减相应 nbdev
        倍滚动标准差。

        预热与输出：满足回看周期前返回前置 NULL；函数只返回 output
        指定的分量，选择分量不会改变底层多输出指标的计算。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        返回 output="upper"：
        >>> tail(ts_talib_bBands(close, 3, 2.0, 2.0, 0, "upper"), 3)
        [12.1776, 12.5933, 12.3828]

        返回 output="middle"：
        >>> tail(ts_talib_bBands(close, 3, 2.0, 2.0, 0, "middle"), 3)
        [11.7667, 11.9333, 12.1333]

        返回 output="lower"：
        >>> tail(ts_talib_bBands(close, 3, 2.0, 2.0, 0, "lower"), 3)
        [11.3557, 11.2734, 11.8839]

        使用 1 倍标准差的上轨：
        >>> tail(ts_talib_bBands(close, 3, 1.0, 1.0, 0, "upper"), 3)
        [11.9721, 12.2633, 12.2581]

        使用 3 倍标准差的下轨：
        >>> tail(ts_talib_bBands(close, 3, 3.0, 3.0, 0, "lower"), 3)
        [11.1502, 10.9434, 11.7592]

        中轨改用 EMA 后返回上轨：
        >>> tail(ts_talib_bBands(close, 3, 2.0, 2.0, 1, "upper"), 3)
        [12.1518, 12.6804, 12.3097]

        中轨改用 WMA：
        >>> tail(ts_talib_bBands(close, 3, 2.0, 2.0, 2, "middle"), 3)
        [11.8, 12.0667, 12.15]
        */
        middle = talib_moving_average(col, time_period, ma_type)
        deviation = ta::stddev(col, int(time_period), 1)
        values = (middle + nbdev_up * deviation, middle, middle - nbdev_down * deviation)
        if (output == "upper") return values[0]
        if (output == "middle") return values[1]
        return values[2]
    }
    """,
    dependencies=(TALIB_MOVING_AVERAGE,),
)

TS_TALIB_BETA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_beta(high, low, time_period) {
        /*
        计算 TA-Lib BETA（滚动 beta）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            第一条按时间升序排列的数值序列；参数名沿用 TA 接口。
        low : vector
            与 high 等长的第二条数值序列；参数名沿用 TA 接口。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：在滚动窗口内计算 covar(left,right) / var(left)，衡量 right 对
        left 的敏感度。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_beta(high, low, 2), 3)
        [1.09902, 1.10591, 1.09469]

        time_period=3：
        >>> tail(ts_talib_beta(high, low, 3), 3)
        [1.09917, 1.09849, 1.09757]

        time_period=5：
        >>> tail(ts_talib_beta(high, low, 5), 3)
        [1.10162, 1.10071, 1.09836]
        */
        return ta::beta(high, low, int(time_period))
    }
    """
)

TS_TALIB_BOP = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_bop(open, high, low, close) {
        /*
        计算 TA-Lib BOP（力量均衡指标）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        open : vector
            开盘价向量。
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：每行所需的任一价格输入为 NULL 时，该行结果为 NULL；函数不前向填充 OHLC 输入。

        计算定义：逐行计算 (close-open)/(high-low)，衡量收盘价在当日价格区间中的买卖力量。

        输出边界：这是逐行价格变换，不需要预热期；结果与输入等长，数值公式由 ta::bop 定义。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> open = close - 0.1
        >>> high = close + 0.6
        >>> low = close - 0.5
        >>> tail(ts_talib_bop(open, high, low, close), 3)
        [0.0909091, 0.0909091, 0.0909091]

        NULL 输入示例：
        >>> open=double([1,NULL]); high=double([3,3]); low=double([0,0]); close=double([2,2])
        >>> ts_talib_bop(open, high, low, close)
        [0.333333, NULL]
        */
        result = ta::bop(open, high, low, close)
        valid = isValid(open) && isValid(high) && isValid(low) && isValid(close)
        return iif(valid, result, double(NULL))
    }
    """
)

TS_TALIB_CCI = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_cci(high, low, close, time_period) {
        /*
        计算 TA-Lib CCI（顺势指标）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：以典型价格为基础，计算其相对移动均值和平均绝对偏差的标准化距离，常数因子为 0.015。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_cci(high, low, close, 2), 3)
        [66.6667, 66.6667, -66.6667]

        time_period=3：
        >>> tail(ts_talib_cci(high, low, close, 3), 3)
        [87.5, 84.6154, -20]

        time_period=5：
        >>> tail(ts_talib_cci(high, low, close, 5), 3)
        [105.263, 119.048, 45.977]
        */
        return ta::cci(high, low, close, int(time_period))
    }
    """
)

TS_TALIB_CORREL = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_correl(high, low, time_period) {
        /*
        计算 TA-Lib CORREL（滚动 Pearson 相关系数）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            第一条按时间升序排列的数值序列；参数名沿用 TA 接口。
        low : vector
            与 high 等长的第二条数值序列；参数名沿用 TA 接口。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：在 time_period 窗口内计算 left 与 right 的 Pearson 相关系数。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_correl(high, low, 2), 3)
        [1, 1, 1]

        time_period=3：
        >>> tail(ts_talib_correl(high, low, 3), 3)
        [1, 1, 1]

        time_period=5：
        >>> tail(ts_talib_correl(high, low, 5), 3)
        [1, 1, 1]
        */
        return ta::correl(high, low, int(time_period))
    }
    """
)

TS_TALIB_DEMA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_dema(col, time_period) {
        /*
        计算 TA-Lib DEMA（双指数移动平均）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 2 * EMA(col) - EMA(EMA(col))，以降低普通 EMA 的滞后。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_dema(close, 2), 3)
        [11.9587, 12.2872, 12.1516]

        time_period=3：
        >>> tail(ts_talib_dema(close, 3), 3)
        [11.9446, 12.2621, 12.2009]

        time_period=5：
        >>> tail(ts_talib_dema(close, 5), 3)
        [11.9462, 12.2346, 12.259]
        */
        return ta::dema(col, int(time_period))
    }
    """
)

TS_TALIB_DX = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_dx(high, low, close, time_period) {
        /*
        计算 TA-Lib DX（趋向指数）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 100 * abs(+DI - -DI) / (+DI + -DI)，只刻画方向运动差异的强度。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_dx(high, low, close, 2), 3)
        [61.1239, 77.2323, 14.1616]

        time_period=3：
        >>> tail(ts_talib_dx(high, low, close, 3), 3)
        [57.3137, 68.9242, 32.8025]

        time_period=5：
        >>> tail(ts_talib_dx(high, low, close, 5), 3)
        [55.5548, 62.9101, 43.1661]
        */
        return ta::dx(high, low, close, int(time_period))
    }
    """
)

TS_TALIB_EMA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_ema(col, time_period) {
        /*
        计算 TA-Lib EMA（指数移动平均）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：使用 alpha = 2/(time_period+1) 递推平滑历史值，近期观测权重更高。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_ema(close, 2), 3)
        [11.8458, 12.1486, 12.1162]

        time_period=3：
        >>> tail(ts_talib_ema(close, 3), 3)
        [11.7409, 12.0204, 12.0602]

        time_period=5：
        >>> tail(ts_talib_ema(close, 5), 3)
        [11.5327, 11.7884, 11.8923]
        */
        return ta::ema(col, int(time_period))
    }
    """
)

TS_TALIB_KAMA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_kama(col, time_period) {
        /*
        计算 TA-Lib KAMA（Kaufman 自适应移动平均）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：根据价格变化效率比动态调整平滑系数；趋势稳定时响应更快，噪声较大时更平滑。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_kama(close, 2), 3)
        [11.3059, 11.7477, 11.7598]

        time_period=3：
        >>> tail(ts_talib_kama(close, 3), 3)
        [11.1127, 11.2485, 11.4029]

        time_period=5：
        >>> tail(ts_talib_kama(close, 5), 3)
        [11.4182, 11.6265, 11.6728]
        */
        return ta::kama(col, int(time_period))
    }
    """
)

TS_TALIB_LINEARREG = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_linearreg(col, time_period) {
        /*
        计算 TA-Lib LINEARREG（滚动线性回归预测值）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：在每个滚动窗口内以位置序号为自变量做 OLS，并返回窗口末端的拟合值。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_linearreg(close, 2), 3)
        [12, 12.3, 12.1]

        time_period=3：
        >>> tail(ts_talib_linearreg(close, 3), 3)
        [11.8667, 12.3333, 12.1833]

        time_period=5：
        >>> tail(ts_talib_linearreg(close, 5), 3)
        [11.98, 12.2, 12.22]
        */
        return ta::linearreg(col, int(time_period))
    }
    """
)

TS_TALIB_LINEARREG_ANGLE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_linearreg_angle(col, time_period) {
        /*
        计算 TA-Lib LINEARREG_ANGLE（滚动线性回归角度）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：对滚动 OLS 斜率取 atan 并转换为角度，表达拟合趋势的倾斜程度。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_linearreg_angle(close, 2), 3)
        [26.5651, 16.6992, -11.3099]

        time_period=3：
        >>> tail(ts_talib_linearreg_angle(close, 3), 3)
        [5.71059, 21.8014, 2.86241]

        time_period=5：
        >>> tail(ts_talib_linearreg_angle(close, 5), 3)
        [12.9528, 11.3099, 7.96961]
        */
        return ta::linearreg_angle(col, int(time_period))
    }
    """
)

TS_TALIB_LINEARREG_INTERCEPT = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_linearreg_intercept(col, time_period) {
        /*
        计算 TA-Lib LINEARREG_INTERCEPT（滚动线性回归截距）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：返回每个滚动位置序号 OLS 拟合直线的截距。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_linearreg_intercept(close, 2), 3)
        [11.5, 12, 12.3]

        time_period=3：
        >>> tail(ts_talib_linearreg_intercept(close, 3), 3)
        [11.6667, 11.5333, 12.0833]

        time_period=5：
        >>> tail(ts_talib_linearreg_intercept(close, 5), 3)
        [11.06, 11.4, 11.66]
        */
        return ta::linearreg_intercept(col, int(time_period))
    }
    """
)

TS_TALIB_LINEARREG_SLOPE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_linearreg_slope(col, time_period) {
        /*
        计算 TA-Lib LINEARREG_SLOPE（滚动线性回归斜率）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：返回每个滚动位置序号 OLS 拟合直线的斜率。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_linearreg_slope(close, 2), 3)
        [0.5, 0.3, -0.2]

        time_period=3：
        >>> tail(ts_talib_linearreg_slope(close, 3), 3)
        [0.1, 0.4, 0.05]

        time_period=5：
        >>> tail(ts_talib_linearreg_slope(close, 5), 3)
        [0.23, 0.2, 0.14]
        */
        return ta::linearreg_slope(col, int(time_period))
    }
    """
)

TS_TALIB_MA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_ma(col, time_period, ma_type) {
        /*
        计算 TA-Lib MA（移动平均）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。
        ma_type : int, default 0
            TA-Lib 移动平均类型编号：0=SMA、1=EMA、2=WMA、3=DEMA、4=TEMA、5=TRIMA、6=KAMA、8=T3。
            当前 DolphinDB 后端不支持 7=MAMA，模型会在构造阶段拒绝；T3 使用 TA-Lib 标准的 0.7 成交量因子。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：按 ma_type 选择 TA 移动平均算法，并使用 time_period 作为回看周期。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        SMA，time_period=2：
        >>> tail(ts_talib_ma(close, 2, 0), 3)
        [11.75, 12.15, 12.2]

        SMA，time_period=3：
        >>> tail(ts_talib_ma(close, 3, 0), 3)
        [11.7667, 11.9333, 12.1333]

        SMA，time_period=5：
        >>> tail(ts_talib_ma(close, 5, 0), 3)
        [11.52, 11.8, 11.94]

        EMA，time_period=3：
        >>> tail(ts_talib_ma(close, 3, 1), 3)
        [11.7409, 12.0204, 12.0602]

        WMA，time_period=3：
        >>> tail(ts_talib_ma(close, 3, 2), 3)
        [11.8, 12.0667, 12.15]

        DEMA，time_period=3：
        >>> tail(ts_talib_ma(close, 3, 3), 3)
        [11.9446, 12.2621, 12.2009]

        TEMA，time_period=2：
        >>> tail(ts_talib_ma(close, 2, 4), 3)
        [11.9734, 12.3006, 12.1217]

        TRIMA，time_period=2：
        >>> tail(ts_talib_ma(close, 2, 5), 3)
        [11.75, 12.15, 12.2]

        KAMA，time_period=2：
        >>> tail(ts_talib_ma(close, 2, 6), 3)
        [11.3059, 11.7477, 11.7598]

        T3，time_period=2：
        >>> tail(ts_talib_ma(close, 2, 8), 3)
        [11.9171, 12.2516, 12.23]
        */
        return talib_moving_average(col, time_period, ma_type)
    }
    """,
    dependencies=(TALIB_MOVING_AVERAGE,),
)

TS_TALIB_MACD = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_macd(col, fast_period, slow_period, signal_period, output) {
        /*
        计算 TA-Lib MACD（移动平均收敛散度）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        底层指标产生多个向量，output 只选择其中一个返回。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        fast_period : int, default 12
            快线周期，必须小于 slow_period。
        slow_period : int, default 26
            慢线周期，必须大于 fast_period。
        signal_period : int, default 9
            MACD 信号线的指数移动平均周期。
        output : {"macd", "signal", "hist"}, default "macd"
            每次调用只返回一个输出向量：
            * "macd"：快线减慢线。
            * "signal"：MACD 的信号移动平均。
            * "hist"：MACD 减信号线。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：以快 EMA 减慢 EMA 得到 MACD，signal 为 MACD 的 EMA，hist 为 MACD
        减 signal。

        预热与输出：满足回看周期前返回前置 NULL；函数只返回 output
        指定的分量，选择分量不会改变底层多输出指标的计算。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        返回 output="macd"：
        >>> tail(ts_talib_macd(close, 2, 4, 2, "macd"), 3)
        [0.207153, 0.245444, 0.134317]

        返回 output="signal"：
        >>> tail(ts_talib_macd(close, 2, 4, 2, "signal"), 3)
        [0.197262, 0.229383, 0.166006]

        返回 output="hist"：
        >>> tail(ts_talib_macd(close, 2, 4, 2, "hist"), 3)
        [0.00989077, 0.0160607, -0.0316887]

        使用 3/6/2 周期返回 MACD：
        >>> tail(ts_talib_macd(close, 3, 6, 2, "macd"), 3)
        [0.308273, 0.338945, 0.258621]

        使用 3/6/3 周期返回信号线：
        >>> tail(ts_talib_macd(close, 3, 6, 3, "signal"), 3)
        [0.314383, 0.326664, 0.292643]
        */
        values = ta::macd(col, int(fast_period), int(slow_period), int(signal_period))
        if (output == "macd") return values[0]
        if (output == "signal") return values[1]
        return values[2]
    }
    """
)

TS_TALIB_MEDPRICE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_medPrice(high, low) {
        /*
        计算 TA-Lib MEDPRICE（中位价格）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：每行所需的任一价格输入为 NULL 时，该行结果为 NULL；函数不前向填充 OHLC 输入。

        计算定义：逐行计算 (high + low) / 2。

        输出边界：这是逐行价格变换，不需要预热期；结果与输入等长，数值公式由 ta::medPrice 定义。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5
        >>> tail(ts_talib_medPrice(high, low), 3)
        [12.05, 12.35, 12.15]

        NULL 输入示例：
        >>> high=double([3,NULL]); low=double([1,2])
        >>> ts_talib_medPrice(high, low)
        [2, NULL]
        */
        return ta::medPrice(high, low)
    }
    """
)

TS_TALIB_MFI = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_mfi(high, low, close, volume, time_period) {
        /*
        计算 TA-Lib MFI（资金流量指标）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        volume : vector
            成交量向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：按典型价格与成交量构造正负资金流，并将资金流比率映射到 0 到 100。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5
        >>> volume = long(1000 1200 900 1300 1400 1100 1500 1600 1250 1700 1800 1550)

        time_period=2：
        >>> tail(ts_talib_mfi(high, low, close, volume, 2), 3)
        [58.6599, 100, 54.1375]

        time_period=3：
        >>> tail(ts_talib_mfi(high, low, close, volume, 3), 3)
        [73.2065, 74.7401, 69.4018]

        time_period=5：
        >>> tail(ts_talib_mfi(high, low, close, volume, 5), 3)
        [68.1342, 84.5243, 64.9592]
        */
        return ta::mfi(high, low, close, volume, int(time_period))
    }
    """
)

TS_TALIB_MIDPOINT = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_midPoint(col, time_period) {
        /*
        计算 TA-Lib MIDPOINT（区间中点）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：返回 time_period 内滚动最高值与滚动最低值的平均数。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_midPoint(close, 2), 3)
        [11.75, 12.15, 12.2]

        time_period=3：
        >>> tail(ts_talib_midPoint(close, 3), 3)
        [11.75, 11.9, 12.15]

        time_period=5：
        >>> tail(ts_talib_midPoint(close, 5), 3)
        [11.45, 11.85, 11.9]
        */
        return ta::midPoint(col, int(time_period))
    }
    """
)

TS_TALIB_MIDPRICE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_midPrice(high, low, time_period) {
        /*
        计算 TA-Lib MIDPRICE（最高价与最低价区间中点）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：返回 time_period 内滚动最高 high 与滚动最低 low 的平均数。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_midPrice(high, low, 2), 3)
        [11.8, 12.2, 12.25]

        time_period=3：
        >>> tail(ts_talib_midPrice(high, low, 3), 3)
        [11.8, 11.95, 12.2]

        time_period=5：
        >>> tail(ts_talib_midPrice(high, low, 5), 3)
        [11.5, 11.9, 11.95]
        */
        return ta::midPrice(high, low, int(time_period))
    }
    """
)

TS_TALIB_MINUS_DI = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_minus_di(high, low, close, time_period) {
        /*
        计算 TA-Lib MINUS_DI（负向指标）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：以真实波幅归一化并平滑负方向运动，得到 -DI。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_minus_di(high, low, close, 2), 3)
        [7.50222, 3.74878, 10.9675]

        time_period=3：
        >>> tail(ts_talib_minus_di(high, low, close, 3), 3)
        [7.92333, 5.25222, 9.5946]

        time_period=5：
        >>> tail(ts_talib_minus_di(high, low, close, 5), 3)
        [8.12448, 6.41826, 8.86424]
        */
        return ta::minus_di(high, low, close, int(time_period))
    }
    """
)

TS_TALIB_MINUS_DM = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_minus_dm(high, low, time_period) {
        /*
        计算 TA-Lib MINUS_DM（负向运动）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：提取 low 相对前一期下降且占优的负方向运动，再按周期平滑。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_minus_dm(high, low, 2), 3)
        [0.164844, 0.0824219, 0.241211]

        time_period=3：
        >>> tail(ts_talib_minus_dm(high, low, 3), 3)
        [0.257064, 0.171376, 0.314251]

        time_period=5：
        >>> tail(ts_talib_minus_dm(high, low, 5), 3)
        [0.420224, 0.336179, 0.468943]
        */
        return ta::minus_dm(high, low, int(time_period))
    }
    """
)

TS_TALIB_MOM = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_mom(col, time_period) {
        /*
        计算 TA-Lib MOM（动量）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：返回当前值减去 time_period 期前数值的价格动量。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_mom(close, 2), 3)
        [0.2, 0.8, 0.1]

        time_period=3：
        >>> tail(ts_talib_mom(close, 3), 3)
        [0.6, 0.5, 0.6]

        time_period=5：
        >>> tail(ts_talib_mom(close, 5), 3)
        [0.9, 1.4, 0.7]
        */
        return ta::mom(col, int(time_period))
    }
    """
)

TS_TALIB_NATR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_natr(high, low, close, time_period) {
        /*
        计算 TA-Lib NATR（归一化平均真实波幅）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        time_period : int
            技术指标观察周期，必须为至少 2 的整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 100 * ATR / close，把真实波幅转换为相对价格百分比。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_natr(high, low, close, 2), 3)
        [9.17318, 8.94627, 9.09252]

        time_period=3：
        >>> tail(ts_talib_natr(high, low, close, 3), 3)
        [9.19105, 8.95895, 9.10166]

        time_period=5：
        >>> tail(ts_talib_natr(high, low, close, 5), 3)
        [9.23493, 8.99637, 9.13424]
        */
        return ta::natr(high, low, close, int(time_period))
    }
    """
)

TS_TALIB_OBV = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_obv(close, volume) {
        /*
        计算 TA-Lib OBV（能量潮）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        close : vector
            收盘价向量。
        volume : vector
            成交量向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充，而是原样交给 TA 状态函数；缺失行可能保持上一累计状态，而不保证在同位置返回
        NULL。需要完整输入时应通过 on 显式排除不完整行。

        计算定义：价格上涨时累加 volume、下跌时扣减 volume、持平时保持，形成累计能量潮。

        状态边界：这是累计状态指标，不需要固定窗口预热；当前输出可能依赖此前全部观测，因此中间缺失值的影响可能延续到后续位置
        。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> volume = long(1000 1200 900 1300 1400 1100 1500 1600 1250 1700 1800 1550)
        >>> tail(ts_talib_obv(close, volume), 3)
        [6450, 8250, 6700]

        NULL 输入示例：
        >>> close=double([1,NULL,2,3]); volume=long([10,20,30,40])
        >>> ts_talib_obv(close, volume)
        [10, 30, 30, 70]
        */
        return ta::obv(close, volume)
    }
    """
)

TS_TALIB_PLUS_DI = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_plus_di(high, low, close, time_period) {
        /*
        计算 TA-Lib PLUS_DI（正向指标）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：以真实波幅归一化并平滑正方向运动，得到 +DI。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_plus_di(high, low, close, 2), 3)
        [31.0933, 29.1818, 14.5864]

        time_period=3：
        >>> tail(ts_talib_plus_di(high, low, close, 3), 3)
        [29.2002, 28.5504, 18.9618]

        time_period=5：
        >>> tail(ts_talib_plus_di(high, low, close, 5), 3)
        [28.4351, 28.191, 22.3293]
        */
        return ta::plus_di(high, low, close, int(time_period))
    }
    """
)

TS_TALIB_PLUS_DM = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_plus_dm(high, low, time_period) {
        /*
        计算 TA-Lib PLUS_DM（正向运动）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：提取 high 相对前一期上升且占优的正方向运动，再按周期平滑。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_plus_dm(high, low, 2), 3)
        [0.683203, 0.641602, 0.320801]

        time_period=3：
        >>> tail(ts_talib_plus_dm(high, low, 3), 3)
        [0.947371, 0.931581, 0.621054]

        time_period=5：
        >>> tail(ts_talib_plus_dm(high, low, 5), 3)
        [1.47075, 1.4766, 1.18128]
        */
        return ta::plus_dm(high, low, int(time_period))
    }
    """
)

TS_TALIB_PPO = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_ppo(col, fast_period, slow_period, ma_type) {
        /*
        计算 TA-Lib PPO（百分比价格振荡器）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        fast_period : int, default 12
            快线周期，必须小于 slow_period。
        slow_period : int, default 26
            慢线周期，必须大于 fast_period。
        ma_type : int, default 0
            TA-Lib 移动平均类型编号：0=SMA、1=EMA、2=WMA、3=DEMA、4=TEMA、5=TRIMA、6=KAMA、8=T3。
            当前 DolphinDB 后端不支持 7=MAMA，模型会在构造阶段拒绝；T3 使用 TA-Lib 标准的 0.7 成交量因子。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 100 * (fastMA - slowMA) / slowMA，以百分比表达快慢均线差。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        2/4 周期的简单移动平均：
        >>> tail(ts_talib_ppo(close, 2, 4, 0), 3)
        [0.642398, 2.10084, 1.87891]

        3/6 周期的简单移动平均：
        >>> tail(ts_talib_ppo(close, 3, 6, 0), 3)
        [2.76565, 2.43205, 2.391]

        2/4 周期的指数移动平均：
        >>> tail(ts_talib_ppo(close, 2, 4, 1), 3)
        [1.78113, 2.06242, 1.12114]

        2/4 周期的加权移动平均：
        >>> tail(ts_talib_ppo(close, 2, 4, 2), 3)
        [0.70922, 1.66667, 0.717439]
        */
        fast = talib_moving_average(col, fast_period, ma_type)
        slow = talib_moving_average(col, slow_period, ma_type)
        return (fast - slow) / slow * 100
    }
    """,
    dependencies=(TALIB_MOVING_AVERAGE,),
)

TS_TALIB_ROC = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_roc(col, time_period) {
        /*
        计算 TA-Lib ROC（变化率）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 100 * (col / lag(col,time_period) - 1)。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_roc(close, 2), 3)
        [1.69492, 6.95652, 0.833333]

        time_period=3：
        >>> tail(ts_talib_roc(close, 3), 3)
        [5.26316, 4.23729, 5.21739]

        time_period=5：
        >>> tail(ts_talib_roc(close, 5), 3)
        [8.10811, 12.844, 6.14035]
        */
        return ta::roc(col, int(time_period))
    }
    """
)

TS_TALIB_ROCP = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_rocp(col, time_period) {
        /*
        计算 TA-Lib ROCP（百分比变化率）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 col / lag(col,time_period) - 1，返回未乘 100 的变化比例。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_rocp(close, 2), 3)
        [0.0169492, 0.0695652, 0.00833333]

        time_period=3：
        >>> tail(ts_talib_rocp(close, 3), 3)
        [0.0526316, 0.0423729, 0.0521739]

        time_period=5：
        >>> tail(ts_talib_rocp(close, 5), 3)
        [0.0810811, 0.12844, 0.0614035]
        */
        return ta::rocp(col, int(time_period))
    }
    """
)

TS_TALIB_ROCR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_rocr(col, time_period) {
        /*
        计算 TA-Lib ROCR（变化率比值）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 col / lag(col,time_period)，1 表示没有变化。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_rocr(close, 2), 3)
        [1.01695, 1.06957, 1.00833]

        time_period=3：
        >>> tail(ts_talib_rocr(close, 3), 3)
        [1.05263, 1.04237, 1.05217]

        time_period=5：
        >>> tail(ts_talib_rocr(close, 5), 3)
        [1.08108, 1.12844, 1.0614]
        */
        return ta::rocr(col, int(time_period))
    }
    """
)

TS_TALIB_ROCR100 = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_rocr100(col, time_period) {
        /*
        计算 TA-Lib ROCR100（百分制变化率比值）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 100 * col / lag(col,time_period)，100 表示没有变化。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_rocr100(close, 2), 3)
        [101.695, 106.957, 100.833]

        time_period=3：
        >>> tail(ts_talib_rocr100(close, 3), 3)
        [105.263, 104.237, 105.217]

        time_period=5：
        >>> tail(ts_talib_rocr100(close, 5), 3)
        [108.108, 112.844, 106.14]
        */
        return ta::rocr100(col, int(time_period))
    }
    """
)

TS_TALIB_RSI = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_rsi(col, time_period) {
        /*
        计算 TA-Lib RSI（相对强弱指标）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：根据 Wilder 平滑的平均上涨和平均下跌计算 100 - 100/(1+RS)，结果通常位于 0 到
        100。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_rsi(close, 2), 3)
        [80.6066, 88.6315, 57.1181]

        time_period=3：
        >>> tail(ts_talib_rsi(close, 3), 3)
        [78.3488, 84.1557, 66.3583]

        time_period=5：
        >>> tail(ts_talib_rsi(close, 5), 3)
        [78.0913, 81.507, 72.1349]
        */
        return ta::rsi(col, int(time_period))
    }
    """
)

TS_TALIB_SMA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_sma(col, time_period) {
        /*
        计算 TA-Lib SMA（简单移动平均）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：对最近 time_period 个观测计算等权算术平均。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_sma(close, 2), 3)
        [11.75, 12.15, 12.2]

        time_period=3：
        >>> tail(ts_talib_sma(close, 3), 3)
        [11.7667, 11.9333, 12.1333]

        time_period=5：
        >>> tail(ts_talib_sma(close, 5), 3)
        [11.52, 11.8, 11.94]
        */
        return ta::sma(col, int(time_period))
    }
    """
)

TS_TALIB_STDDEV = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_stddev(col, time_period, nbdev) {
        /*
        计算 TA-Lib STDDEV（滚动标准差）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。
        nbdev : float, default 1.0
            标准差结果的缩放倍数。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 time_period 窗口标准差并乘以 nbdev。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        nbdev=0.5：
        >>> tail(ts_talib_stddev(close, 3, 0.5), 3)
        [0.10274, 0.164992, 0.062361]

        nbdev=1.0：
        >>> tail(ts_talib_stddev(close, 3, 1.0), 3)
        [0.20548, 0.329983, 0.124722]

        nbdev=2.0：
        >>> tail(ts_talib_stddev(close, 3, 2.0), 3)
        [0.410961, 0.659966, 0.249444]
        */
        return ta::stddev(col, int(time_period), nbdev)
    }
    """
)

TS_TALIB_T3 = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_t3(col, time_period, vfactor) {
        /*
        计算 TA-Lib T3（T3 移动平均）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。
        vfactor : float, default 0.7
            T3 平滑因子，取值范围为 [0, 1]；数值越大，对近期观测的响应通常越强。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：对多层 EMA 使用 vfactor 组合，形成低滞后的 Tillson T3 平滑结果。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        vfactor=0.3：
        >>> tail(ts_talib_t3(close, 2, 0.3), 3)
        [11.7202, 11.9904, 12.0867]

        vfactor=0.7：
        >>> tail(ts_talib_t3(close, 2, 0.7), 3)
        [11.8331, 12.1368, 12.1728]

        vfactor=0.9：
        >>> tail(ts_talib_t3(close, 2, 0.9), 3)
        [11.8891, 12.2128, 12.2117]
        */
        return ta::t3(col, int(time_period), vfactor)
    }
    """
)

TS_TALIB_TEMA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_tema(col, time_period) {
        /*
        计算 TA-Lib TEMA（三重指数移动平均）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 3*EMA1 - 3*EMA2 + EMA3，以三重 EMA 组合降低滞后。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_tema(close, 2), 3)
        [11.9734, 12.3006, 12.1217]

        time_period=3：
        >>> tail(ts_talib_tema(close, 3), 3)
        [11.9492, 12.2834, 12.1611]

        time_period=5：
        >>> tail(ts_talib_tema(close, 5), 3)
        [NULL, NULL, NULL]
        */
        return ta::tema(col, int(time_period))
    }
    """
)

TS_TALIB_TRANGE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_trange(high, low, close) {
        /*
        计算 TA-Lib TRANGE（真实波幅）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：首行因缺少前收盘价返回 NULL；当前 high/low 或参与比较的前收盘价为 NULL
        时，相应位置也无法形成真实波幅。

        计算定义：计算 max(high-low, abs(high-prevClose),
        abs(low-prevClose))。

        输出边界：结果依赖当前 high/low 和前一期 close，因此首个位置没有真实波幅；输出与输入等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5
        >>> tail(ts_talib_trange(high, low, close), 3)
        [1.1, 1.1, 1.1]

        NULL 输入示例：
        >>> high=double([2,NULL,4]); low=double([0,1,2]); close=double([1,2,3])
        >>> ts_talib_trange(high, low, close)
        [NULL, NULL, 2]
        */
        return ta::trange(high, low, close)
    }
    """
)

TS_TALIB_TRIMA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_trima(col, time_period) {
        /*
        计算 TA-Lib TRIMA（三角移动平均）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：使用三角形权重计算移动平均，窗口中部观测权重最高。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_trima(close, 2), 3)
        [11.75, 12.15, 12.2]

        time_period=3：
        >>> tail(ts_talib_trima(close, 3), 3)
        [11.7, 11.95, 12.175]

        time_period=5：
        >>> tail(ts_talib_trima(close, 5), 3)
        [11.5667, 11.7556, 11.9444]
        */
        return ta::trima(col, int(time_period))
    }
    """
)

TS_TALIB_TRIX = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_trix(col, time_period) {
        /*
        计算 TA-Lib TRIX（三重指数平滑变化率）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：对三重 EMA 计算一期变化率，用于过滤短期噪声并观察趋势动量。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_trix(close, 2), 3)
        [1.7182, 2.15096, 1.09886]

        time_period=3：
        >>> tail(ts_talib_trix(close, 3), 3)
        [1.78664, 1.94317, 1.56171]

        time_period=5：
        >>> tail(ts_talib_trix(close, 5), 3)
        [NULL, NULL, NULL]
        */
        return ta::trix(col, int(time_period))
    }
    """
)

TS_TALIB_TSF = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_tsf(col, time_period) {
        /*
        计算 TA-Lib TSF（时间序列预测）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：在滚动窗口内做位置序号 OLS，并把拟合直线向窗口末端之后的下一个位置外推。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_tsf(close, 2), 3)
        [12.5, 12.6, 11.9]

        time_period=3：
        >>> tail(ts_talib_tsf(close, 3), 3)
        [11.9667, 12.7333, 12.2333]

        time_period=5：
        >>> tail(ts_talib_tsf(close, 5), 3)
        [12.21, 12.4, 12.36]
        */
        return ta::tsf(col, int(time_period))
    }
    """
)

TS_TALIB_TYPPRICE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_typPrice(high, low, close) {
        /*
        计算 TA-Lib TYPPRICE（典型价格）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：每行所需的任一价格输入为 NULL 时，该行结果为 NULL；函数不前向填充 OHLC 输入。

        计算定义：逐行计算 (high + low + close) / 3。

        输出边界：这是逐行价格变换，不需要预热期；结果与输入等长，数值公式由 ta::typPrice 定义。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5
        >>> tail(ts_talib_typPrice(high, low, close), 3)
        [12.0333, 12.3333, 12.1333]

        NULL 输入示例：
        >>> high=double([3,NULL]); low=double([1,2]); close=double([2,3])
        >>> ts_talib_typPrice(high, low, close)
        [2, NULL]
        */
        return ta::typPrice(high, low, close)
    }
    """
)

TS_TALIB_ULTOSC = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_ultOsc(high, low, close, period1, period2, period3) {
        /*
        计算 TA-Lib ULTOSC（终极振荡器）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        period1 : int, default 7
            终极振荡器的短周期；必须满足 period1 < period2 < period3。
        period2 : int, default 14
            终极振荡器的中周期；必须满足 period1 < period2 < period3。
        period3 : int, default 28
            终极振荡器的长周期；必须满足 period1 < period2 < period3。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：分别在 period1/period2/period3 上累计买压与真实波幅，再按 4:2:1
        加权并缩放到 0 到 100。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        周期组合 2/3/5：
        >>> tail(ts_talib_ultOsc(high, low, close, 2, 3, 5), 3)
        [45.4545, 45.4545, 45.4545]

        周期组合 3/5/7：
        >>> tail(ts_talib_ultOsc(high, low, close, 3, 5, 7), 3)
        [45.5544, 45.4545, 45.4545]

        周期组合 4/6/8：
        >>> tail(ts_talib_ultOsc(high, low, close, 4, 6, 8), 3)
        [45.5421, 45.5421, 45.4545]
        */
        return ta::ultOsc(high, low, close, int(period1), int(period2), int(period3))
    }
    """
)

TS_TALIB_VAR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_var(col, time_period, nbdev) {
        /*
        计算 TA-Lib VAR（滚动方差）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。
        nbdev : float, default 1.0
            标准差结果的缩放倍数。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 time_period 窗口方差，并按 TA-Lib 的 nbdev 参数缩放。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        nbdev=0.5：
        >>> tail(ts_talib_var(close, 3, 0.5), 3)
        [0.0422222, 0.108889, 0.0155556]

        nbdev=1.0：
        >>> tail(ts_talib_var(close, 3, 1.0), 3)
        [0.0422222, 0.108889, 0.0155556]

        nbdev=2.0：
        >>> tail(ts_talib_var(close, 3, 2.0), 3)
        [0.0422222, 0.108889, 0.0155556]
        */
        return ta::var(col, int(time_period), nbdev)
    }
    """
)

TS_TALIB_WCLPRICE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_wclPrice(high, low, close) {
        /*
        计算 TA-Lib WCLPRICE（加权收盘价）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：每行所需的任一价格输入为 NULL 时，该行结果为 NULL；函数不前向填充 OHLC 输入。

        计算定义：逐行计算 (high + low + 2*close) / 4，使收盘价权重为其他价格的两倍。

        输出边界：这是逐行价格变换，不需要预热期；结果与输入等长，数值公式由 ta::wclPrice 定义。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5
        >>> tail(ts_talib_wclPrice(high, low, close), 3)
        [12.025, 12.325, 12.125]

        NULL 输入示例：
        >>> high=double([3,NULL]); low=double([1,2]); close=double([2,3])
        >>> ts_talib_wclPrice(high, low, close)
        [2, NULL]
        */
        return ta::wclPrice(high, low, close)
    }
    """
)

TS_TALIB_WILLR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_willr(high, low, close, time_period) {
        /*
        计算 TA-Lib WILLR（Williams %R）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        high : vector
            最高价向量。
        low : vector
            最低价向量。
        close : vector
            收盘价向量。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：计算 -100 *
        (windowHigh-close)/(windowHigh-windowLow)，结果通常位于 -100 到 0。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1
        >>> high = close + 0.6
        >>> low = close - 0.5

        time_period=2：
        >>> tail(ts_talib_willr(high, low, close, 2), 3)
        [-37.5, -42.8571, -61.5385]

        time_period=3：
        >>> tail(ts_talib_willr(high, low, close, 3), 3)
        [-37.5, -31.5789, -57.1429]

        time_period=5：
        >>> tail(ts_talib_willr(high, low, close, 5), 3)
        [-27.2727, -30, -42.1053]
        */
        return ta::willr(high, low, close, int(time_period))
    }
    """
)

TS_TALIB_WMA = DolphinDBFunction(
    module="query",
    definition="""
    def ts_talib_wma(col, time_period) {
        /*
        计算 TA-Lib WMA（加权移动平均）。

        该函数直接调用 DolphinDB TA-Lib 实现。所有输入向量必须等长；指标尚未积累足够历史观测的预热位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的数值序列。
        time_period : int
            技术指标观察周期，必须为正整数；预热期通常返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：输入不在算符内填充；TA 函数缺少形成当前指标所需的有效历史时返回 NULL，后续何时恢复由该 ta
        内置函数的窗口状态决定。

        计算定义：使用从 1 到 time_period 递增的线性权重计算移动平均，近期观测权重最高。

        预热与输出：满足指标所需回看周期前返回前置 NULL；周期越长，首个有效结果通常越晚，输出始终与输入序列等长。

        Examples
        --------
        >>> close = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8 11.5 12.0 12.3 12.1

        time_period=2：
        >>> tail(ts_talib_wma(close, 2), 3)
        [11.8333, 12.2, 12.1667]

        time_period=3：
        >>> tail(ts_talib_wma(close, 3), 3)
        [11.8, 12.0667, 12.15]

        time_period=5：
        >>> tail(ts_talib_wma(close, 5), 3)
        [11.6733, 11.9333, 12.0333]
        */
        return ta::wma(col, int(time_period))
    }
    """
)

TS_UNARY_BARS_SINCE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_bars_since(col) {
        /*
        计算每个位置距最近一次 true 的观测间隔。

        遇到 true 时计数重置为 0，之后每经过一个观测加 1；首次 true 之前没有可用距离，返回 NULL。

        Parameters
        ----------
        col : vector[BOOL]
            按时间升序排列的条件向量；不接受价格等数值列。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：BOOL NULL 按未触发事件处理；首次 true 之前返回 NULL，首次触发后 NULL
        位置会继续增加距上次触发的间隔。

        计数语义：触发当期返回 0，之后按观测行数递增，不按自然日差计算。

        Examples
        --------
        >>> col = false true true false true true true false
        >>> ts_unary_bars_since(col)
        [NULL, 0, 0, 1, 0, 0, 0, 1]

        NULL 按未触发事件处理：
        >>> ts_unary_bars_since(bool([false, NULL, true, false, NULL]))
        [NULL, NULL, 0, 1, 2]
        */
        if (type(col) != BOOL) throw "条件型算符的 col 必须是 BOOL"
        n = size(col)
        if (n == 0) return array(INT, 0, 0)
        positions = 0..(n - 1)
        last_position = cummax(iif(nullFill(col, false), positions, int(NULL)))
        return iif(isNull(last_position), int(NULL), positions - last_position)
    }
    """
)

TS_UNARY_BFILL = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_bfill(col, limit) {
        /*
        使用后续非 NULL 值向前填充缺失值。

        每段连续 NULL 使用后续最近的非 NULL 值填充。limit 只限制单段连续 NULL 最多填充多少个位置。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        limit : int or NULL, default NULL
            每段连续 NULL 最多填充的数量；NULL 表示不限制。

        Returns
        -------
        result : vector
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：使用后一个非 NULL 值填充连续缺失位置；没有可用来源的边界 NULL 保持不变。limit 为
        NULL 时不限制连续填充数量。

        限制语义：limit 只限制每段连续 NULL 可填充的个数，不限制整条序列的累计填充次数；非 NULL
        原值不会被修改。

        Examples
        --------
        >>> col = 1.0 2.0 3.0 4.0 5.0 6.0
        >>> col[1 2 4] = NULL

        不限制连续填充数量：
        >>> ts_unary_bfill(col, int(NULL))
        [1, 4, 4, 4, 6, 6]

        最多连续填充 1 个 NULL：
        >>> ts_unary_bfill(col, 1)
        [1, NULL, 4, 4, 6, 6]

        最多连续填充 2 个 NULL：
        >>> ts_unary_bfill(col, 2)
        [1, 4, 4, 4, 6, 6]
        */
        if (isNull(limit)) return bfill(col)
        return bfill(col, int(limit))
    }
    """
)

TS_UNARY_CHANGED = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_changed(col, null_equal) {
        /*
        标记当前值是否相对上一观测发生变化。

        第一个位置固定为 true。一个值为 NULL、另一个非 NULL 时结果为 true；连续两个 NULL 是否算变化由 null_equal 决定。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        null_equal : bool, default false
            true 时两个连续 NULL 不算变化；false 时仍标记为变化。

        Returns
        -------
        result : vector[BOOL]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：当前值与前值一空一非空时视为发生变化；两者均为 NULL 时由 null_equal
        决定是否视为相同。首个观测始终返回 true。

        比较语义：逐位置与紧邻前一观测比较，不跨过 NULL，也不对浮点数使用容差。

        Examples
        --------
        >>> col = 1.0 1.0 2.0 3.0 4.0 4.0
        >>> col[3 4] = NULL

        连续 NULL 仍视为变化：
        >>> ts_unary_changed(col, false)
        [true, false, true, true, true, true]

        连续 NULL 视为相等：
        >>> ts_unary_changed(col, true)
        [true, false, true, true, false, true]
        */
        n = size(col)
        result = array(BOOL, n, n, false)
        if (n == 0) return result
        previous = move(col, 1)
        current_null = isNull(col)
        previous_null = isNull(previous)
        both_null = current_null && previous_null
        one_null = xor(current_null, previous_null)
        result = iif(one_null, true, iif(both_null, !null_equal, col != previous))
        result[0] = true
        return result
    }
    """
)

TS_UNARY_CONSECUTIVE_COUNT = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_consecutive_count(col) {
        /*
        统计当前位置连续为 true 的观测数。

        true 使计数在上一位置基础上加 1，false 将计数重置为 0，BOOL NULL 保持上一计数。

        Parameters
        ----------
        col : vector[BOOL]
            按时间升序排列的条件向量；不接受价格等数值列。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：BOOL NULL 不会新增 true，也不会把已有连续计数清零，而是保持上一计数；false
        才会将计数重置为 0。

        计数语义：true 在上一状态上加 1，结果按观测行计数。若需要 NULL 直接中断连续段，应先把 NULL
        显式转换为 false。

        Examples
        --------
        >>> col = false true true false true true true false
        >>> ts_unary_consecutive_count(col)
        [0, 1, 2, 0, 1, 2, 3, 0]

        NULL 保持已有连续计数：
        >>> ts_unary_consecutive_count(bool([true, NULL, true, true, false]))
        [1, 1, 2, 3, 0]
        */
        if (type(col) != BOOL) throw "条件型算符的 col 必须是 BOOL"
        return cumPositiveStreak(col)
    }
    """
)

TS_UNARY_CUM_COUNT = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_cum_count(col, min_periods) {
        /*
        计算截至当前位置的非 NULL 累计数量。

        第 i 个结果使用从序列起点到当前位置的有效观测。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：NULL 不计入累计有效值数量，当前位置返回截至该行的非 NULL 计数。

        累计边界：统计从序列首个观测开始，状态不会自动重置；输出与输入等长，数值类型和溢出行为由对应 DolphinDB
        累计函数决定。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=1：
        >>> ts_unary_cum_count(col, 1)
        [1, 2, 3, 4, 5, 6, 7, 8]

        min_periods=3：
        >>> ts_unary_cum_count(col, 3)
        [NULL, NULL, 3, 4, 5, 6, 7, 8]
        */
        result = cumcount(col)
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_CUM_MAX = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_cum_max(col, min_periods) {
        /*
        计算截至当前位置的累计最大值。

        第 i 个结果使用从序列起点到当前位置的有效观测。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：累计统计跳过 NULL；当前位置为 NULL 时仍可返回此前有效观测形成的累计结果。

        累计边界：统计从序列首个观测开始，状态不会自动重置；输出与输入等长，数值类型和溢出行为由对应 DolphinDB
        累计函数决定。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=1：
        >>> ts_unary_cum_max(col, 1)
        [1, 2, 4, 4, 5, 7, 7, 8]

        min_periods=3：
        >>> ts_unary_cum_max(col, 3)
        [NULL, NULL, 4, 4, 5, 7, 7, 8]
        */
        result = cummax(col)
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_CUM_MEAN = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_cum_mean(col, min_periods) {
        /*
        计算截至当前位置的累计平均值。

        第 i 个结果使用从序列起点到当前位置的有效观测。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：累计统计跳过 NULL；当前位置为 NULL 时仍可返回此前有效观测形成的累计结果。

        累计边界：统计从序列首个观测开始，状态不会自动重置；输出与输入等长，数值类型和溢出行为由对应 DolphinDB
        累计函数决定。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=1：
        >>> ts_unary_cum_mean(col, 1)
        [1, 1.5, 2.33333, 2.5, 3, 3.66667, 4, 4.5]

        min_periods=3：
        >>> ts_unary_cum_mean(col, 3)
        [NULL, NULL, 2.33333, 2.5, 3, 3.66667, 4, 4.5]
        */
        result = cumavg(col)
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_CUM_MIN = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_cum_min(col, min_periods) {
        /*
        计算截至当前位置的累计最小值。

        第 i 个结果使用从序列起点到当前位置的有效观测。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：累计统计跳过 NULL；当前位置为 NULL 时仍可返回此前有效观测形成的累计结果。

        累计边界：统计从序列首个观测开始，状态不会自动重置；输出与输入等长，数值类型和溢出行为由对应 DolphinDB
        累计函数决定。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=1：
        >>> ts_unary_cum_min(col, 1)
        [1, 1, 1, 1, 1, 1, 1, 1]

        min_periods=3：
        >>> ts_unary_cum_min(col, 3)
        [NULL, NULL, 1, 1, 1, 1, 1, 1]
        */
        result = cummin(col)
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_CUM_PROD = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_cum_prod(col, min_periods) {
        /*
        计算截至当前位置的累计乘积。

        第 i 个结果使用从序列起点到当前位置的有效观测。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：累计统计跳过 NULL；当前位置为 NULL 时仍可返回此前有效观测形成的累计结果。

        累计边界：统计从序列首个观测开始，状态不会自动重置；输出与输入等长，数值类型和溢出行为由对应 DolphinDB
        累计函数决定。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=1：
        >>> ts_unary_cum_prod(col, 1)
        [1, 2, 8, 24, 120, 840, 5040, 40320]

        min_periods=3：
        >>> ts_unary_cum_prod(col, 3)
        [NULL, NULL, 8, 24, 120, 840, 5040, 40320]
        */
        result = cumprod(col)
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_CUM_SUM = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_cum_sum(col, min_periods) {
        /*
        计算截至当前位置的累计和。

        第 i 个结果使用从序列起点到当前位置的有效观测。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：累计统计跳过 NULL；当前位置为 NULL 时仍可返回此前有效观测形成的累计结果。

        累计边界：统计从序列首个观测开始，状态不会自动重置；输出与输入等长，数值类型和溢出行为由对应 DolphinDB
        累计函数决定。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=1：
        >>> ts_unary_cum_sum(col, 1)
        [1, 3, 7, 10, 15, 22, 28, 36]

        min_periods=3：
        >>> ts_unary_cum_sum(col, 3)
        [NULL, NULL, 7, 10, 15, 22, 28, 36]
        */
        result = cumsum(col)
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_DECAY_LINEAR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_decay_linear(col, window, min_periods) {
        /*
        使用线性递增权重计算滚动平均。

        窗口内从最早到最新的观测依次使用 1, 2, ..., window 的权重；NULL 对应的权重不进入分子和分母。该算符只计算完整窗口，
        因此前 window - 1 个位置始终为 NULL。min_periods 控制完整窗口内至少需要多少个非 NULL 观测。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            完整窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：加权窗口平均跳过 NULL，并对剩余有效权重重新归一化；有效观测少于 min_periods 时返回
        NULL。

        权重语义：窗口内权重从最旧观测的 1 线性增加到当前观测的 window，窗口右对齐；min_periods 为
        NULL 时要求完整窗口。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        三期窗口，最新观测权重最大：
        >>> ts_unary_decay_linear(col, 3, 1)
        [NULL, NULL, 2.83333, 3.16667, 4.16667, 5.66667, 6.16667, 7.16667]

        min_periods=NULL 要求完整窗口内没有 NULL：
        >>> ts_unary_decay_linear(col, 3, int(NULL))
        [NULL, NULL, 2.83333, 3.16667, 4.16667, 5.66667, 6.16667, 7.16667]

        两期窗口使用 1:2 权重：
        >>> ts_unary_decay_linear(col, 2, 2)
        [NULL, 1.66667, 3.33333, 3.33333, 4.33333, 6.33333, 6.33333, 7.33333]

        完整窗口中存在 NULL 时，剩余有效权重重新归一化：
        >>> ts_unary_decay_linear(1.0 NULL 4.0 3.0 5.0, 3, 2)
        [NULL, NULL, 3.25, 3.4, 4.16667]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mavg(col, double(1..int(window)), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_DIFF = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_diff(col, periods) {
        /*
        计算当前值与指定期数前观测的差。

        periods 按观测条数而不是自然日计数。没有足够历史观测的位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        periods : int, default 1
            向后比较或位移的观测期数，必须至少为 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：当前值或滞后值为 NULL 时结果为 NULL。本算符不跨越缺失观测寻找更早的有效值。

        位置语义：periods 表示序列中的观测间隔，不表示日历天数；前 periods 个位置通常因缺少滞后值而为
        NULL。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        periods=1：
        >>> ts_unary_diff(col, 1)
        [NULL, 1, 2, -1, 2, 2, -1, 2]

        periods=2：
        >>> ts_unary_diff(col, 2)
        [NULL, NULL, 3, 1, 1, 4, 1, 1]

        periods=3：
        >>> ts_unary_diff(col, 3)
        [NULL, NULL, NULL, 2, 3, 3, 3, 3]
        */
        return deltas(col, int(periods))
    }
    """
)

TS_UNARY_EWM_MEAN = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_ewm_mean(col, com, span, half_life, alpha, min_periods, adjust, ignore_na) {
        /*
        计算指数加权移动平均。

        com、span、half_life 和 alpha 必须且只能提供一个，它们最终确定同一个平滑系数。结果与输入等长，并从序列起点递推或按完整权重计算。

        min_periods 控制首个非 NULL 结果所需的有效观测数；adjust 控制归一化权重形式；ignore_na 控制 NULL 是否占用权重位置。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        com : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 1 / (1 + com)，com >= 0。
        span : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 2 / (span + 1)，span >= 1。
        half_life : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 1 - exp(log(0.5) / half_life)，half_life > 0。
        alpha : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。直接指定平滑系数，0 < alpha <= 1。
        min_periods : int, default 0
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。
        adjust : bool, default true
            true 时使用显式衰减权重并除以权重和；false 时使用递归更新形式。
        ignore_na : bool, default false
            false 时权重按绝对位置计算，NULL 仍占用位置；true 时权重只按有效观测的相对位置计算。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Raises
        ------
        DolphinDB exception
            未提供任何 EWM 衰减参数时抛出异常。正常 DSL 构造会在 Python 校验阶段阻止该输入。

        Notes
        -----
        NULL 处理：输入 NULL 不会被填充。ignore_na=false
        时缺失位置仍影响后续权重距离，ignore_na=true 时仅按有效观测的相对位置累计权重；min_periods
        统计非 NULL 观测。

        衰减与边界：com、span、half_life、alpha 必须且只能提供一个。adjust=true
        使用归一化的显式历史权重，adjust=false 使用递推形式；四种衰减参数只是 alpha 的不同表达。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        使用 com 指定衰减：
        >>> ts_unary_ewm_mean(col, 1.0, double(NULL), double(NULL), double(NULL), 1, true, false)
        [1, 1.66667, 3, 3, 4.03226, 5.53968, 5.77165, 6.8902]

        使用 span 指定衰减：
        >>> ts_unary_ewm_mean(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false)
        [1, 1.66667, 3, 3, 4.03226, 5.53968, 5.77165, 6.8902]

        使用 half_life 指定衰减：
        >>> ts_unary_ewm_mean(col, double(NULL), double(NULL), 2.0, double(NULL), 1, true, false)
        [1, 1.58579, 2.67962, 2.80474, 3.58579, 4.72864, 5.13712, 6.03154]

        使用 alpha 指定衰减：
        >>> ts_unary_ewm_mean(col, double(NULL), double(NULL), double(NULL), 0.5, 1, true, false)
        [1, 1.66667, 3, 3, 4.03226, 5.53968, 5.77165, 6.8902]

        adjust=false 使用递归形式：
        >>> ts_unary_ewm_mean(col, double(NULL), 3.0, double(NULL), double(NULL), 1, false, false)
        [1, 1.5, 2.75, 2.875, 3.9375, 5.46875, 5.73438, 6.86719]

        min_periods=3 延后首个有效结果：
        >>> ts_unary_ewm_mean(col, double(NULL), 3.0, double(NULL), double(NULL), 3, true, false)
        [NULL, NULL, 3, 3, 4.03226, 5.53968, 5.77165, 6.8902]

        >>> col = 1.0 2.0 3.0 4.0 5.0 6.0
        >>> col[1 3] = NULL

        ignore_na=false 按绝对位置计算权重：
        >>> ts_unary_ewm_mean(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false)
        [1, 1, 2.6, 2.6, 4.42857, 5.37736]

        ignore_na=true 按有效观测的相对位置计算权重：
        >>> ts_unary_ewm_mean(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, true)
        [1, 1, 2.33333, 2.33333, 3.85714, 5]
        */
        if (!isNull(com)) return ewmMean(col, com, , , , int(min_periods), adjust, ignore_na)
        if (!isNull(span)) return ewmMean(col, , span, , , int(min_periods), adjust, ignore_na)
        if (!isNull(half_life)) return ewmMean(col, , , half_life, , int(min_periods), adjust, ignore_na)
        if (!isNull(alpha)) return ewmMean(col, , , , alpha, int(min_periods), adjust, ignore_na)
        throw "EWM 必须提供一个衰减参数"
    }
    """
)

TS_UNARY_EWM_STD = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_ewm_std(col, com, span, half_life, alpha, min_periods, adjust, ignore_na, bias) {
        /*
        计算指数加权移动标准差。

        com、span、half_life 和 alpha 必须且只能提供一个，它们最终确定同一个平滑系数。结果与输入等长，并从序列起点递推或按完整权重计算。

        min_periods 控制首个非 NULL 结果所需的有效观测数；adjust 控制归一化权重形式；ignore_na 控制 NULL 是否占用权重位置。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        com : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 1 / (1 + com)，com >= 0。
        span : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 2 / (span + 1)，span >= 1。
        half_life : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 1 - exp(log(0.5) / half_life)，half_life > 0。
        alpha : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。直接指定平滑系数，0 < alpha <= 1。
        min_periods : int, default 0
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。
        adjust : bool, default true
            true 时使用显式衰减权重并除以权重和；false 时使用递归更新形式。
        ignore_na : bool, default false
            false 时权重按绝对位置计算，NULL 仍占用位置；true 时权重只按有效观测的相对位置计算。
        bias : bool, default false
            true 使用有偏估计；false 对有限样本进行无偏修正。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Raises
        ------
        DolphinDB exception
            未提供任何 EWM 衰减参数时抛出异常。正常 DSL 构造会在 Python 校验阶段阻止该输入。

        Notes
        -----
        NULL 处理：输入 NULL 不会被填充。ignore_na=false
        时缺失位置仍影响后续权重距离，ignore_na=true 时仅按有效观测的相对位置累计权重；min_periods
        统计非 NULL 观测。

        衰减与边界：com、span、half_life、alpha 必须且只能提供一个。bias
        控制是否使用有偏估计；有效样本不足以估计尺度时返回 NULL。四种衰减参数只是 alpha 的不同表达。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        使用 com 指定衰减：
        >>> ts_unary_ewm_std(col, 1.0, double(NULL), double(NULL), double(NULL), 1, true, false, false)
        [NULL, 0.707107, 1.58114, 1.0351, 1.43122, 2.0848, 1.48956, 1.72338]

        使用 span 指定衰减：
        >>> ts_unary_ewm_std(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, false)
        [NULL, 0.707107, 1.58114, 1.0351, 1.43122, 2.0848, 1.48956, 1.72338]

        使用 half_life 指定衰减：
        >>> ts_unary_ewm_std(col, double(NULL), double(NULL), 2.0, double(NULL), 1, true, false, false)
        [NULL, 0.707107, 1.5688, 1.17484, 1.51814, 2.19437, 1.90963, 2.15886]

        使用 alpha 指定衰减：
        >>> ts_unary_ewm_std(col, double(NULL), double(NULL), double(NULL), 0.5, 1, true, false, false)
        [NULL, 0.707107, 1.58114, 1.0351, 1.43122, 2.0848, 1.48956, 1.72338]

        adjust=false 使用递归形式：
        >>> ts_unary_ewm_std(col, double(NULL), 3.0, double(NULL), double(NULL), 1, false, false, false)
        [NULL, 0.707107, 1.64317, 1.14434, 1.53201, 2.16578, 1.56507, 1.77469]

        min_periods=3 延后首个有效结果：
        >>> ts_unary_ewm_std(col, double(NULL), 3.0, double(NULL), double(NULL), 3, true, false, false)
        [NULL, NULL, 1.58114, 1.0351, 1.43122, 2.0848, 1.48956, 1.72338]

        bias=false 使用无偏估计：
        >>> ts_unary_ewm_std(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, false)
        [NULL, 0.707107, 1.58114, 1.0351, 1.43122, 2.0848, 1.48956, 1.72338]

        bias=true 使用有偏估计：
        >>> ts_unary_ewm_std(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, true)
        [0, 0.471405, 1.19523, 0.816497, 1.14958, 1.68867, 1.21142, 1.40437]

        >>> col = 1.0 2.0 3.0 4.0 5.0 6.0
        >>> col[1 3] = NULL

        ignore_na=false 按绝对位置计算权重：
        >>> ts_unary_ewm_std(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, false)
        [NULL, NULL, 1.41421, 1.41421, 1.77281, 1.40671]

        ignore_na=true 按有效观测的相对位置计算权重：
        >>> ts_unary_ewm_std(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, true, false)
        [NULL, NULL, 1.41421, 1.41421, 1.92725, 1.85164]
        */
        if (!isNull(com)) return ewmStd(col, com, , , , int(min_periods), adjust, ignore_na, bias)
        if (!isNull(span)) return ewmStd(col, , span, , , int(min_periods), adjust, ignore_na, bias)
        if (!isNull(half_life)) return ewmStd(col, , , half_life, , int(min_periods), adjust, ignore_na, bias)
        if (!isNull(alpha)) return ewmStd(col, , , , alpha, int(min_periods), adjust, ignore_na, bias)
        throw "EWM 必须提供一个衰减参数"
    }
    """
)

TS_UNARY_EWM_VAR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_ewm_var(col, com, span, half_life, alpha, min_periods, adjust, ignore_na, bias) {
        /*
        计算指数加权移动方差。

        com、span、half_life 和 alpha 必须且只能提供一个，它们最终确定同一个平滑系数。结果与输入等长，并从序列起点递推或按完整权重计算。

        min_periods 控制首个非 NULL 结果所需的有效观测数；adjust 控制归一化权重形式；ignore_na 控制 NULL 是否占用权重位置。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        com : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 1 / (1 + com)，com >= 0。
        span : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 2 / (span + 1)，span >= 1。
        half_life : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。alpha = 1 - exp(log(0.5) / half_life)，half_life > 0。
        alpha : float or NULL, default NULL
            指数加权衰减参数；四个参数必须且只能提供一个。直接指定平滑系数，0 < alpha <= 1。
        min_periods : int, default 0
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。
        adjust : bool, default true
            true 时使用显式衰减权重并除以权重和；false 时使用递归更新形式。
        ignore_na : bool, default false
            false 时权重按绝对位置计算，NULL 仍占用位置；true 时权重只按有效观测的相对位置计算。
        bias : bool, default false
            true 使用有偏估计；false 对有限样本进行无偏修正。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Raises
        ------
        DolphinDB exception
            未提供任何 EWM 衰减参数时抛出异常。正常 DSL 构造会在 Python 校验阶段阻止该输入。

        Notes
        -----
        NULL 处理：输入 NULL 不会被填充。ignore_na=false
        时缺失位置仍影响后续权重距离，ignore_na=true 时仅按有效观测的相对位置累计权重；min_periods
        统计非 NULL 观测。

        衰减与边界：com、span、half_life、alpha 必须且只能提供一个。bias
        控制是否使用有偏估计；有效样本不足以估计尺度时返回 NULL。四种衰减参数只是 alpha 的不同表达。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        使用 com 指定衰减：
        >>> ts_unary_ewm_var(col, 1.0, double(NULL), double(NULL), double(NULL), 1, true, false, false)
        [NULL, 0.5, 2.5, 1.07143, 2.04839, 4.34639, 2.21879, 2.97003]

        使用 span 指定衰减：
        >>> ts_unary_ewm_var(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, false)
        [NULL, 0.5, 2.5, 1.07143, 2.04839, 4.34639, 2.21879, 2.97003]

        使用 half_life 指定衰减：
        >>> ts_unary_ewm_var(col, double(NULL), double(NULL), 2.0, double(NULL), 1, true, false, false)
        [NULL, 0.5, 2.46113, 1.38025, 2.30474, 4.81527, 3.6467, 4.66066]

        使用 alpha 指定衰减：
        >>> ts_unary_ewm_var(col, double(NULL), double(NULL), double(NULL), 0.5, 1, true, false, false)
        [NULL, 0.5, 2.5, 1.07143, 2.04839, 4.34639, 2.21879, 2.97003]

        adjust=false 使用递归形式：
        >>> ts_unary_ewm_var(col, double(NULL), 3.0, double(NULL), double(NULL), 1, false, false, false)
        [NULL, 0.5, 2.7, 1.30952, 2.34706, 4.69062, 2.44945, 3.14951]

        min_periods=3 延后首个有效结果：
        >>> ts_unary_ewm_var(col, double(NULL), 3.0, double(NULL), double(NULL), 3, true, false, false)
        [NULL, NULL, 2.5, 1.07143, 2.04839, 4.34639, 2.21879, 2.97003]

        bias=false 使用无偏估计：
        >>> ts_unary_ewm_var(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, false)
        [NULL, 0.5, 2.5, 1.07143, 2.04839, 4.34639, 2.21879, 2.97003]

        bias=true 使用有偏估计：
        >>> ts_unary_ewm_var(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, true)
        [0, 0.222222, 1.42857, 0.666667, 1.32154, 2.8516, 1.46754, 1.97226]

        >>> col = 1.0 2.0 3.0 4.0 5.0 6.0
        >>> col[1 3] = NULL

        ignore_na=false 按绝对位置计算权重：
        >>> ts_unary_ewm_var(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, false, false)
        [NULL, NULL, 2, 2, 3.14286, 1.97884]

        ignore_na=true 按有效观测的相对位置计算权重：
        >>> ts_unary_ewm_var(col, double(NULL), 3.0, double(NULL), double(NULL), 1, true, true, false)
        [NULL, NULL, 2, 2, 3.71429, 3.42857]
        */
        if (!isNull(com)) return ewmVar(col, com, , , , int(min_periods), adjust, ignore_na, bias)
        if (!isNull(span)) return ewmVar(col, , span, , , int(min_periods), adjust, ignore_na, bias)
        if (!isNull(half_life)) return ewmVar(col, , , half_life, , int(min_periods), adjust, ignore_na, bias)
        if (!isNull(alpha)) return ewmVar(col, , , , alpha, int(min_periods), adjust, ignore_na, bias)
        throw "EWM 必须提供一个衰减参数"
    }
    """
)

TS_UNARY_EXPANDING_MEDIAN = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_expanding_median(col, min_periods) {
        /*
        计算从序列起点到当前位置的扩展中位数。

        第 i 个结果使用从序列首个观测到第 i 个观测的全部历史。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：累计统计忽略 NULL，min_periods 按非 NULL 观测数判断；达到门槛后，当前输入为
        NULL 也可能返回已有历史形成的统计值。

        扩展窗口：每个位置使用从序列起点到当前位置的全部历史，旧观测不会滚出窗口。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=1：
        >>> ts_unary_expanding_median(col, 1)
        [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5]

        min_periods=3：
        >>> ts_unary_expanding_median(col, 3)
        [NULL, NULL, 2, 2.5, 3, 3.5, 4, 4.5]

        min_periods=5：
        >>> ts_unary_expanding_median(col, 5)
        [NULL, NULL, NULL, NULL, 3, 3.5, 4, 4.5]
        */
        result = cummed(col)
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_EXPANDING_QUANTILE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_expanding_quantile(col, min_periods, q) {
        /*
        计算从序列起点到当前位置的扩展分位数。

        第 i 个结果使用从序列首个观测到第 i 个观测的全部历史。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。
        q : float
            目标分位数，取值范围为 [0, 1]。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：累计统计忽略 NULL，min_periods 按非 NULL 观测数判断；达到门槛后，当前输入为
        NULL 也可能返回已有历史形成的统计值。

        扩展窗口：q 在每个累计窗口内独立应用，必须位于模型允许的分位数范围。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=1：
        >>> ts_unary_expanding_quantile(col, 1, 0.5)
        [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5]

        min_periods=3：
        >>> ts_unary_expanding_quantile(col, 3, 0.5)
        [NULL, NULL, 2, 2.5, 3, 3.5, 4, 4.5]

        min_periods=5：
        >>> ts_unary_expanding_quantile(col, 5, 0.5)
        [NULL, NULL, NULL, NULL, 3, 3.5, 4, 4.5]
        */
        result = cumpercentile(col, 100 * q)
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_EXPANDING_RANK = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_expanding_rank(col, min_periods, ascending, ties_method) {
        /*
        计算当前值在截至当前位置样本中的扩展排名。

        第 i 个结果使用从序列首个观测到第 i 个观测的全部历史。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。
        ascending : bool, default true
            true 时最小值排名最前；false 时最大值排名最前。
        ties_method : {"min", "max", "average", "dense"}, default "min"
            并列值处理方式：
            * "min"：并列组使用该组的最小名次。
            * "max"：并列组使用该组的最大名次。
            * "average"：并列组使用所占名次的平均值。
            * "dense"：类似 "min"，但下一组名次只增加 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：历史统计会忽略 NULL，但当前位置为 NULL 时排名结果仍为 NULL；min_periods
        按累计非 NULL 数量判断。

        扩展窗口：ascending 和 ties_method 决定当前值在累计有效样本中的排名方式。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        ties_method="min"：
        >>> ts_unary_expanding_rank(col, 1, true, "min")
        [1, 2, 3, 3, 5, 6, 6, 8]

        ties_method="max"：
        >>> ts_unary_expanding_rank(col, 1, true, "max")
        [1, 2, 3, 3, 5, 6, 6, 8]

        ties_method="average"：
        >>> ts_unary_expanding_rank(col, 1, true, "average")
        [1, 2, 3, 3, 5, 6, 6, 8]

        ties_method="dense"：
        >>> ts_unary_expanding_rank(col, 1, true, "dense")
        [1, 2, 3, 3, 5, 6, 6, 8]

        降序排名：
        >>> ts_unary_expanding_rank(col, 1, false, "min")
        [1, 1, 1, 2, 1, 1, 2, 1]
        */
        if (ties_method == "dense") {
            result = cumdenseRank(col, ascending, true, false)
        } else {
            result = cumrank(col, ascending, true, ties_method, false)
        }
        if (!false) result = result + 1
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_EXPANDING_RANK_PCT = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_expanding_rank_pct(col, min_periods, ascending, ties_method) {
        /*
        计算当前值在截至当前位置样本中的扩展百分位排名。

        第 i 个结果使用从序列首个观测到第 i 个观测的全部历史。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。
        ascending : bool, default true
            true 时最小值排名最前；false 时最大值排名最前。
        ties_method : {"min", "max", "average", "dense"}, default "min"
            并列值处理方式：
            * "min"：并列组使用该组的最小名次。
            * "max"：并列组使用该组的最大名次。
            * "average"：并列组使用所占名次的平均值。
            * "dense"：类似 "min"，但下一组名次只增加 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：历史统计会忽略 NULL，但当前位置为 NULL 时排名结果仍为 NULL；min_periods
        按累计非 NULL 数量判断。

        扩展窗口：ascending 和 ties_method 决定当前值在累计有效样本中的排名方式。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        ties_method="min"：
        >>> ts_unary_expanding_rank_pct(col, 1, true, "min")
        [1, 1, 1, 0.75, 1, 1, 0.857143, 1]

        ties_method="max"：
        >>> ts_unary_expanding_rank_pct(col, 1, true, "max")
        [1, 1, 1, 0.75, 1, 1, 0.857143, 1]

        ties_method="average"：
        >>> ts_unary_expanding_rank_pct(col, 1, true, "average")
        [1, 1, 1, 0.75, 1, 1, 0.857143, 1]

        ties_method="dense"：
        >>> ts_unary_expanding_rank_pct(col, 1, true, "dense")
        [1, 1, 1, 0.75, 1, 1, 0.857143, 1]

        降序排名：
        >>> ts_unary_expanding_rank_pct(col, 1, false, "min")
        [1, 0.5, 0.333333, 0.5, 0.2, 0.166667, 0.285714, 0.125]
        */
        if (ties_method == "dense") {
            result = cumdenseRank(col, ascending, true, true)
        } else {
            result = cumrank(col, ascending, true, ties_method, true)
        }
        if (!true) result = result + 1
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_EXPANDING_SEM = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_expanding_sem(col, min_periods) {
        /*
        计算从序列起点到当前位置的均值标准误。

        第 i 个结果使用从序列首个观测到第 i 个观测的全部历史。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：累计统计忽略 NULL，min_periods 按非 NULL 观测数判断；达到门槛后，当前输入为
        NULL 也可能返回已有历史形成的统计值。

        扩展窗口：每个位置使用从序列起点到当前位置的全部历史，旧观测不会滚出窗口。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=1：
        >>> ts_unary_expanding_sem(col, 1)
        [NULL, 0.5, 0.881917, 0.645497, 0.707107, 0.881917, 0.816497, 0.866025]

        min_periods=3：
        >>> ts_unary_expanding_sem(col, 3)
        [NULL, NULL, 0.881917, 0.645497, 0.707107, 0.881917, 0.816497, 0.866025]

        min_periods=5：
        >>> ts_unary_expanding_sem(col, 5)
        [NULL, NULL, NULL, NULL, 0.707107, 0.881917, 0.816497, 0.866025]
        */
        result = cumstd(col) / sqrt(cumcount(col))
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_EXPANDING_STD = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_expanding_std(col, min_periods) {
        /*
        计算从序列起点到当前位置的扩展标准差。

        第 i 个结果使用从序列首个观测到第 i 个观测的全部历史。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：累计统计忽略 NULL，min_periods 按非 NULL 观测数判断；达到门槛后，当前输入为
        NULL 也可能返回已有历史形成的统计值。

        扩展窗口：每个位置使用从序列起点到当前位置的全部历史，旧观测不会滚出窗口。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=1：
        >>> ts_unary_expanding_std(col, 1)
        [NULL, 0.707107, 1.52753, 1.29099, 1.58114, 2.16025, 2.16025, 2.44949]

        min_periods=3：
        >>> ts_unary_expanding_std(col, 3)
        [NULL, NULL, 1.52753, 1.29099, 1.58114, 2.16025, 2.16025, 2.44949]

        min_periods=5：
        >>> ts_unary_expanding_std(col, 5)
        [NULL, NULL, NULL, NULL, 1.58114, 2.16025, 2.16025, 2.44949]
        */
        result = cumstd(col)
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_EXPANDING_VAR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_expanding_var(col, min_periods) {
        /*
        计算从序列起点到当前位置的扩展方差。

        第 i 个结果使用从序列首个观测到第 i 个观测的全部历史。累计有效观测数小于 min_periods 时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        min_periods : int, default 1
            产生结果所需的累计非 NULL 观测数。未达到该数量的位置返回 NULL。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：累计统计忽略 NULL，min_periods 按非 NULL 观测数判断；达到门槛后，当前输入为
        NULL 也可能返回已有历史形成的统计值。

        扩展窗口：每个位置使用从序列起点到当前位置的全部历史，旧观测不会滚出窗口。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=1：
        >>> ts_unary_expanding_var(col, 1)
        [NULL, 0.5, 2.33333, 1.66667, 2.5, 4.66667, 4.66667, 6]

        min_periods=3：
        >>> ts_unary_expanding_var(col, 3)
        [NULL, NULL, 2.33333, 1.66667, 2.5, 4.66667, 4.66667, 6]

        min_periods=5：
        >>> ts_unary_expanding_var(col, 5)
        [NULL, NULL, NULL, NULL, 2.5, 4.66667, 4.66667, 6]
        */
        result = cumvar(col)
        return mask_expanding_result(result, col, min_periods)
    }
    """,
    dependencies=(MASK_EXPANDING_RESULT,)
)

TS_UNARY_FFILL = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_ffill(col, limit) {
        /*
        使用此前最近的非 NULL 值向后填充缺失值。

        每段连续 NULL 使用此前最近的非 NULL 值填充。limit 只限制单段连续 NULL 最多填充多少个位置。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        limit : int or NULL, default NULL
            每段连续 NULL 最多填充的数量；NULL 表示不限制。

        Returns
        -------
        result : vector
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：使用前一个非 NULL 值填充连续缺失位置；没有可用来源的边界 NULL 保持不变。limit 为
        NULL 时不限制连续填充数量。

        限制语义：limit 只限制每段连续 NULL 可填充的个数，不限制整条序列的累计填充次数；非 NULL
        原值不会被修改。

        Examples
        --------
        >>> col = 1.0 2.0 3.0 4.0 5.0 6.0
        >>> col[1 2 4] = NULL

        不限制连续填充数量：
        >>> ts_unary_ffill(col, int(NULL))
        [1, 1, 1, 4, 4, 6]

        最多连续填充 1 个 NULL：
        >>> ts_unary_ffill(col, 1)
        [1, 1, NULL, 4, 4, 6]

        最多连续填充 2 个 NULL：
        >>> ts_unary_ffill(col, 2)
        [1, 1, 1, 4, 4, 6]
        */
        if (isNull(limit)) return ffill(col)
        return ffill(col, int(limit))
    }
    """
)

TS_UNARY_LOG_RETURN = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_log_return(col, periods) {
        /*
        计算指定期数的对数收益率。

        periods 按观测条数而不是自然日计数。没有足够历史观测的位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        periods : int, default 1
            向后比较或位移的观测期数，必须至少为 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：当前值、滞后值为 NULL 或任一值非正时结果为 NULL。本算符不跨越缺失观测寻找更早的有效值。

        位置语义：periods 表示序列中的观测间隔，不表示日历天数；前 periods 个位置通常因缺少滞后值而为
        NULL。

        Examples
        --------
        >>> col = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8

        periods=1：
        >>> ts_unary_log_return(col, 1)
        [NULL, 0.0487902, -0.0289875, 0.0571584, 0.027399, -0.0181823, 0.0448506, 0.0344862]

        periods=2：
        >>> ts_unary_log_return(col, 2)
        [NULL, NULL, 0.0198026, 0.0281709, 0.0845574, 0.00921666, 0.0266682, 0.0793367]

        periods=3：
        >>> ts_unary_log_return(col, 3)
        [NULL, NULL, NULL, 0.076961, 0.0555699, 0.0663751, 0.0540672, 0.0611544]
        */
        return log(col) - move(log(col), int(periods))
    }
    """
)

TS_UNARY_PCT_CHANGE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_pct_change(col, periods) {
        /*
        计算相对指定期数前观测的百分比变化。

        periods 按观测条数而不是自然日计数。没有足够历史观测的位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        periods : int, default 1
            向后比较或位移的观测期数，必须至少为 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：当前值或滞后值为 NULL，以及滞后值为 0 时结果为
        NULL。本算符不跨越缺失观测寻找更早的有效值。

        位置语义：periods 表示序列中的观测间隔，不表示日历天数；前 periods 个位置通常因缺少滞后值而为
        NULL。

        Examples
        --------
        >>> col = 10.0 10.5 10.2 10.8 11.1 10.9 11.4 11.8

        periods=1：
        >>> ts_unary_pct_change(col, 1)
        [NULL, 0.05, -0.0285714, 0.0588235, 0.0277778, -0.018018, 0.0458716, 0.0350877]

        periods=2：
        >>> ts_unary_pct_change(col, 2)
        [NULL, NULL, 0.02, 0.0285714, 0.0882353, 0.00925926, 0.027027, 0.0825688]

        periods=3：
        >>> ts_unary_pct_change(col, 3)
        [NULL, NULL, NULL, 0.08, 0.0571429, 0.0686275, 0.0555556, 0.0630631]
        */
        previous = move(col, int(periods))
        return divide_or_null(col, previous) - 1
    }
    """,
    dependencies=(DIVIDE_OR_NULL,)
)

TS_UNARY_ROLLING_ALL = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_all(col, window, min_periods) {
        /*
        判断窗口内所有有效布尔观测是否均为 true。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector[BOOL]
            按时间升序排列的条件向量；不接受价格等数值列。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[BOOL]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：BOOL NULL 不计入有效观测分母；所有有效观测均为 true 且有效数量达到
        min_periods 时返回 true。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = false true true false true true true false

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_all(col, 3, int(NULL))
        [false, false, false, false, false, false, true, false]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_all(col, 3, 1)
        [false, false, false, false, false, false, true, false]

        min_periods=2：
        >>> ts_unary_rolling_all(col, 3, 2)
        [false, false, false, false, false, false, true, false]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_all(col, 4, 2)
        [false, false, false, false, false, false, false, false]
        */
        minimum = rolling_min_periods(window, min_periods)
        count_true = rolling_true_count(col, window, minimum)
        count_valid = mcount(col, int(window), minimum)
        return (count_valid >= minimum) && (count_true == count_valid)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS, ROLLING_TRUE_COUNT)
)

TS_UNARY_ROLLING_ANY = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_any(col, window, min_periods) {
        /*
        判断窗口内是否至少有一个布尔观测为 true。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector[BOOL]
            按时间升序排列的条件向量；不接受价格等数值列。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[BOOL]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：BOOL NULL 不计为 true；窗口中至少一个有效 true 才返回 true，有效观测数不足
        min_periods 时返回 NULL。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = false true true false true true true false

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_any(col, 3, int(NULL))
        [false, false, true, true, true, true, true, true]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_any(col, 3, 1)
        [false, true, true, true, true, true, true, true]

        min_periods=2：
        >>> ts_unary_rolling_any(col, 3, 2)
        [false, true, true, true, true, true, true, true]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_any(col, 4, 2)
        [false, true, true, true, true, true, true, true]
        */
        minimum = rolling_min_periods(window, min_periods)
        return rolling_true_count(col, window, minimum) > 0
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS, ROLLING_TRUE_COUNT)
)

TS_UNARY_ROLLING_ARGMAX = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_argmax(col, window, min_periods) {
        /*
        返回窗口最大值在窗口内的位置。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_argmax(col, 3, int(NULL))
        [NULL, NULL, 2, 1, 2, 2, 1, 2]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_argmax(col, 3, 1)
        [0, 1, 2, 1, 2, 2, 1, 2]

        min_periods=2：
        >>> ts_unary_rolling_argmax(col, 3, 2)
        [NULL, 1, 2, 1, 2, 2, 1, 2]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_argmax(col, 4, 2)
        [NULL, 1, 2, 2, 3, 3, 2, 3]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mimax(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_ARGMIN = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_argmin(col, window, min_periods) {
        /*
        返回窗口最小值在窗口内的位置。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_argmin(col, 3, int(NULL))
        [NULL, NULL, 0, 0, 1, 0, 0, 1]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_argmin(col, 3, 1)
        [0, 0, 0, 0, 1, 0, 0, 1]

        min_periods=2：
        >>> ts_unary_rolling_argmin(col, 3, 2)
        [NULL, 0, 0, 0, 1, 0, 0, 1]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_argmin(col, 4, 2)
        [NULL, 0, 0, 0, 0, 1, 0, 0]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mimin(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_COUNT = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_count(col, window, min_periods) {
        /*
        统计窗口内的非 NULL 观测数。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_count(col, 3, int(NULL))
        [NULL, NULL, 3, 3, 3, 3, 3, 3]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_count(col, 3, 1)
        [1, 2, 3, 3, 3, 3, 3, 3]

        min_periods=2：
        >>> ts_unary_rolling_count(col, 3, 2)
        [NULL, 2, 3, 3, 3, 3, 3, 3]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_count(col, 4, 2)
        [NULL, 2, 3, 4, 4, 4, 4, 4]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mcount(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_FIRST = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_first(col, window, min_periods) {
        /*
        返回窗口内第一个有效观测。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：min_periods 统计窗口内有效观测，但返回值取窗口起点；该端点本身为 NULL 时结果仍为
        NULL，不会改取窗口内其他有效值。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_first(col, 3, int(NULL))
        [NULL, NULL, 1, 2, 4, 3, 5, 7]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_first(col, 3, 1)
        [1, 1, 1, 2, 4, 3, 5, 7]

        min_periods=2：
        >>> ts_unary_rolling_first(col, 3, 2)
        [NULL, 1, 1, 2, 4, 3, 5, 7]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_first(col, 4, 2)
        [NULL, 1, 1, 1, 2, 4, 3, 5]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mfirst(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_KURT = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_kurt(col, window, min_periods) {
        /*
        计算窗口峰度。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_kurt(col, 3, int(NULL))
        [NULL, NULL, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_kurt(col, 3, 1)
        [NULL, NULL, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5]

        min_periods=2：
        >>> ts_unary_rolling_kurt(col, 3, 2)
        [NULL, NULL, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_kurt(col, 4, 2)
        [NULL, NULL, 1.5, 1.64, 1.64, 1.84571, 1.84571, 1.64]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mkurtosis(col, int(window), true, minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_LAST = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_last(col, window, min_periods) {
        /*
        返回窗口内最后一个有效观测。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：min_periods 统计窗口内有效观测，但返回值取当前位置；该端点本身为 NULL 时结果仍为
        NULL，不会改取窗口内其他有效值。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_last(col, 3, int(NULL))
        [NULL, NULL, 4, 3, 5, 7, 6, 8]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_last(col, 3, 1)
        [1, 2, 4, 3, 5, 7, 6, 8]

        min_periods=2：
        >>> ts_unary_rolling_last(col, 3, 2)
        [NULL, 2, 4, 3, 5, 7, 6, 8]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_last(col, 4, 2)
        [NULL, 2, 4, 3, 5, 7, 6, 8]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mlast(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_MAD = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_mad(col, window, min_periods) {
        /*
        计算窗口中位数绝对离差（MAD）。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        MAD 定义：先求窗口中位数，再求各有效观测与该中位数之差的绝对值的中位数。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_mad(col, 3, int(NULL))
        [NULL, NULL, 1, 1, 1, 2, 1, 1]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_mad(col, 3, 1)
        [0, 0.5, 1, 1, 1, 2, 1, 1]

        min_periods=2：
        >>> ts_unary_rolling_mad(col, 3, 2)
        [NULL, 0.5, 1, 1, 1, 2, 1, 1]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_mad(col, 4, 2)
        [NULL, 0.5, 1, 1, 1, 1, 1, 1]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mmad(col, int(window), true, minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_MAX = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_max(col, window, min_periods) {
        /*
        计算窗口最大值。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_max(col, 3, int(NULL))
        [NULL, NULL, 4, 4, 5, 7, 7, 8]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_max(col, 3, 1)
        [1, 2, 4, 4, 5, 7, 7, 8]

        min_periods=2：
        >>> ts_unary_rolling_max(col, 3, 2)
        [NULL, 2, 4, 4, 5, 7, 7, 8]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_max(col, 4, 2)
        [NULL, 2, 4, 4, 5, 7, 7, 8]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mmax(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_MEAN = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_mean(col, window, min_periods) {
        /*
        计算窗口算术平均值。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_mean(col, 3, int(NULL))
        [NULL, NULL, 2.33333, 3, 4, 5, 6, 7]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_mean(col, 3, 1)
        [1, 1.5, 2.33333, 3, 4, 5, 6, 7]

        min_periods=2：
        >>> ts_unary_rolling_mean(col, 3, 2)
        [NULL, 1.5, 2.33333, 3, 4, 5, 6, 7]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_mean(col, 4, 2)
        [NULL, 1.5, 2.33333, 2.5, 3.5, 4.75, 5.25, 6.5]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mavg(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_MEDIAN = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_median(col, window, min_periods) {
        /*
        计算窗口中位数。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_median(col, 3, int(NULL))
        [NULL, NULL, 2, 3, 4, 5, 6, 7]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_median(col, 3, 1)
        [1, 1.5, 2, 3, 4, 5, 6, 7]

        min_periods=2：
        >>> ts_unary_rolling_median(col, 3, 2)
        [NULL, 1.5, 2, 3, 4, 5, 6, 7]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_median(col, 4, 2)
        [NULL, 1.5, 2, 2.5, 3.5, 4.5, 5.5, 6.5]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mmed(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_MIN = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_min(col, window, min_periods) {
        /*
        计算窗口最小值。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_min(col, 3, int(NULL))
        [NULL, NULL, 1, 2, 3, 3, 5, 6]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_min(col, 3, 1)
        [1, 1, 1, 2, 3, 3, 5, 6]

        min_periods=2：
        >>> ts_unary_rolling_min(col, 3, 2)
        [NULL, 1, 1, 2, 3, 3, 5, 6]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_min(col, 4, 2)
        [NULL, 1, 1, 1, 2, 3, 3, 5]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mmin(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_PROD = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_prod(col, window, min_periods) {
        /*
        计算窗口乘积。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_prod(col, 3, int(NULL))
        [NULL, NULL, 8, 24, 60, 105, 210, 336]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_prod(col, 3, 1)
        [1, 2, 8, 24, 60, 105, 210, 336]

        min_periods=2：
        >>> ts_unary_rolling_prod(col, 3, 2)
        [NULL, 2, 8, 24, 60, 105, 210, 336]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_prod(col, 4, 2)
        [NULL, 2, 8, 24, 120, 420, 630, 1680]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mprod(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_QUANTILE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_quantile(col, window, min_periods, q) {
        /*
        计算窗口分位数。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。
        q : float
            目标分位数，取值范围为 [0, 1]。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_quantile(col, 3, int(NULL), 0.5)
        [NULL, NULL, 2, 3, 4, 5, 6, 7]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_quantile(col, 3, 1, 0.5)
        [1, 1.5, 2, 3, 4, 5, 6, 7]

        min_periods=2：
        >>> ts_unary_rolling_quantile(col, 3, 2, 0.5)
        [NULL, 1.5, 2, 3, 4, 5, 6, 7]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_quantile(col, 4, 2, 0.5)
        [NULL, 1.5, 2, 2.5, 3.5, 4.5, 5.5, 6.5]

        25% 分位数：
        >>> ts_unary_rolling_quantile(col, 3, 2, 0.25)
        [NULL, 1.25, 1.5, 2.5, 3.5, 4, 5.5, 6.5]

        75% 分位数：
        >>> ts_unary_rolling_quantile(col, 3, 2, 0.75)
        [NULL, 1.75, 3, 3.5, 4.5, 6, 6.5, 7.5]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mpercentile(col, 100 * q, int(window), "linear", minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_RANK = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_rank(col, window, min_periods, ascending, ties_method) {
        /*
        计算当前值在窗口内的排名。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        每个位置只返回当前观测在其窗口中的名次，而不是整个窗口的排名向量。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。
        ascending : bool, default true
            true 时最小值排名最前；false 时最大值排名最前。
        ties_method : {"min", "max", "average"}, default "min"
            并列值处理方式：
            * "min"：并列组使用该组的最小名次。
            * "max"：并列组使用该组的最大名次。
            * "average"：并列组使用所占名次的平均值。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口统计忽略历史 NULL，但当前位置为 NULL 时排名为 NULL；min_periods
        按窗口内非 NULL 数量判断。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 3.0 2.0 4.0 4.0 5.0

        ties_method="min"：
        >>> ts_unary_rolling_rank(col, 3, 2, true, "min")
        [NULL, 2, 2, 3, 1, 3, 2, 3]

        ties_method="max"：
        >>> ts_unary_rolling_rank(col, 3, 2, true, "max")
        [NULL, 2, 3, 3, 2, 3, 3, 3]

        ties_method="average"：
        >>> ts_unary_rolling_rank(col, 3, 2, true, "average")
        [NULL, 2, 2.5, 3, 1.5, 3, 2.5, 3]

        降序排名：
        >>> ts_unary_rolling_rank(col, 3, 2, false, "min")
        [NULL, 1, 1, 1, 2, 1, 1, 1]

        min_periods=NULL 时必须先形成完整窗口：
        >>> ts_unary_rolling_rank(col, 3, int(NULL), true, "min")
        [NULL, NULL, 2, 3, 1, 3, 2, 3]

        使用更长的窗口：
        >>> ts_unary_rolling_rank(col, 4, 2, true, "min")
        [NULL, 2, 2, 4, 1, 4, 3, 4]

        窗口含 NULL 时只对有效观测排名：
        >>> ts_unary_rolling_rank(1.0 NULL 2.0 2.0 3.0, 3, 2, true, "average")
        [NULL, NULL, 2, 1.5, 3]
        */
        minimum = rolling_min_periods(window, min_periods)
        result = mrank(col, ascending, int(window), true, ties_method, false, minimum)
        if (!false) result = result + 1
        return result
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_RANK_PCT = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_rank_pct(col, window, min_periods, ascending, ties_method) {
        /*
        计算当前值在窗口内的百分位排名。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        每个位置只返回当前观测在其窗口中的名次，而不是整个窗口的排名向量。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。
        ascending : bool, default true
            true 时最小值排名最前；false 时最大值排名最前。
        ties_method : {"min", "max", "average"}, default "min"
            并列值处理方式：
            * "min"：并列组使用该组的最小名次。
            * "max"：并列组使用该组的最大名次。
            * "average"：并列组使用所占名次的平均值。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口统计忽略历史 NULL，但当前位置为 NULL 时排名为 NULL；min_periods
        按窗口内非 NULL 数量判断。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 3.0 2.0 4.0 4.0 5.0

        ties_method="min"：
        >>> ts_unary_rolling_rank_pct(col, 3, 2, true, "min")
        [NULL, 1, 0.666667, 1, 0.333333, 1, 0.666667, 1]

        ties_method="max"：
        >>> ts_unary_rolling_rank_pct(col, 3, 2, true, "max")
        [NULL, 1, 1, 1, 0.666667, 1, 1, 1]

        ties_method="average"：
        >>> ts_unary_rolling_rank_pct(col, 3, 2, true, "average")
        [NULL, 1, 0.833333, 1, 0.5, 1, 0.833333, 1]

        降序排名：
        >>> ts_unary_rolling_rank_pct(col, 3, 2, false, "min")
        [NULL, 0.5, 0.333333, 0.333333, 0.666667, 0.333333, 0.333333, 0.333333]

        min_periods=NULL 时必须先形成完整窗口：
        >>> ts_unary_rolling_rank_pct(col, 3, int(NULL), true, "min")
        [NULL, NULL, 0.666667, 1, 0.333333, 1, 0.666667, 1]

        使用更长的窗口：
        >>> ts_unary_rolling_rank_pct(col, 4, 2, true, "min")
        [NULL, 1, 0.666667, 1, 0.25, 1, 0.75, 1]

        窗口含 NULL 时只对有效观测排名：
        >>> ts_unary_rolling_rank_pct(1.0 NULL 2.0 2.0 3.0, 3, 2, true, "average")
        [NULL, NULL, 1, 0.75, 1]
        */
        minimum = rolling_min_periods(window, min_periods)
        result = mrank(col, ascending, int(window), true, ties_method, true, minimum)
        if (!true) result = result + 1
        return result
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_SEM = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_sem(col, window, min_periods) {
        /*
        计算窗口均值标准误。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_sem(col, 3, int(NULL))
        [NULL, NULL, 0.881917, 0.57735, 0.57735, 1.1547, 0.57735, 0.57735]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_sem(col, 3, 1)
        [NULL, 0.5, 0.881917, 0.57735, 0.57735, 1.1547, 0.57735, 0.57735]

        min_periods=2：
        >>> ts_unary_rolling_sem(col, 3, 2)
        [NULL, 0.5, 0.881917, 0.57735, 0.57735, 1.1547, 0.57735, 0.57735]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_sem(col, 4, 2)
        [NULL, 0.5, 0.881917, 0.645497, 0.645497, 0.853913, 0.853913, 0.645497]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mstd(col, int(window), minimum) / sqrt(mcount(col, int(window), minimum))
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_SKEW = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_skew(col, window, min_periods) {
        /*
        计算窗口偏度。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_skew(col, 3, int(NULL))
        [NULL, NULL, 0.381802, 0, 0, 0, 0, 0]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_skew(col, 3, 1)
        [NULL, 0, 0.381802, 0, 0, 0, 0, 0]

        min_periods=2：
        >>> ts_unary_rolling_skew(col, 3, 2)
        [NULL, 0, 0.381802, 0, 0, 0, 0, 0]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_skew(col, 4, 2)
        [NULL, 0, 0.381802, 0, 0, 0.434651, -0.434651, 0]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mskew(col, int(window), true, minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_STD = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_std(col, window, min_periods) {
        /*
        计算窗口标准差。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_std(col, 3, int(NULL))
        [NULL, NULL, 1.52753, 1, 1, 2, 1, 1]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_std(col, 3, 1)
        [NULL, 0.707107, 1.52753, 1, 1, 2, 1, 1]

        min_periods=2：
        >>> ts_unary_rolling_std(col, 3, 2)
        [NULL, 0.707107, 1.52753, 1, 1, 2, 1, 1]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_std(col, 4, 2)
        [NULL, 0.707107, 1.52753, 1.29099, 1.29099, 1.70783, 1.70783, 1.29099]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mstd(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_SUM = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_sum(col, window, min_periods) {
        /*
        计算窗口总和。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_sum(col, 3, int(NULL))
        [NULL, NULL, 7, 9, 12, 15, 18, 21]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_sum(col, 3, 1)
        [1, 3, 7, 9, 12, 15, 18, 21]

        min_periods=2：
        >>> ts_unary_rolling_sum(col, 3, 2)
        [NULL, 3, 7, 9, 12, 15, 18, 21]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_sum(col, 4, 2)
        [NULL, 3, 7, 10, 14, 19, 21, 26]
        */
        minimum = rolling_min_periods(window, min_periods)
        return msum(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_TRUE_COUNT = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_true_count(col, window, min_periods) {
        /*
        统计窗口内为 true 的观测数。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector[BOOL]
            按时间升序排列的条件向量；不接受价格等数值列。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：BOOL NULL 在计数前转换为 false，因此不增加 true 的数量；有效观测数仍必须达到
        min_periods。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = false true true false true true true false

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_true_count(col, 3, int(NULL))
        [NULL, NULL, 2, 2, 2, 2, 3, 2]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_true_count(col, 3, 1)
        [0, 1, 2, 2, 2, 2, 3, 2]

        min_periods=2：
        >>> ts_unary_rolling_true_count(col, 3, 2)
        [NULL, 1, 2, 2, 2, 2, 3, 2]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_true_count(col, 4, 2)
        [NULL, 1, 2, 2, 3, 3, 3, 3]
        */
        minimum = rolling_min_periods(window, min_periods)
        return rolling_true_count(col, window, minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS, ROLLING_TRUE_COUNT)
)

TS_UNARY_ROLLING_VAR = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_var(col, window, min_periods) {
        /*
        计算窗口方差。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：窗口聚合跳过 NULL，min_periods 按窗口内非 NULL
        数量判断；达到门槛后，当前位置为 NULL 也可能由同一窗口的其他有效观测产生结果。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_var(col, 3, int(NULL))
        [NULL, NULL, 2.33333, 1, 1, 4, 1, 1]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_var(col, 3, 1)
        [NULL, 0.5, 2.33333, 1, 1, 4, 1, 1]

        min_periods=2：
        >>> ts_unary_rolling_var(col, 3, 2)
        [NULL, 0.5, 2.33333, 1, 1, 4, 1, 1]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_var(col, 4, 2)
        [NULL, 0.5, 2.33333, 1.66667, 1.66667, 2.91667, 2.91667, 1.66667]
        */
        minimum = rolling_min_periods(window, min_periods)
        return mvar(col, int(window), minimum)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_ROLLING_ZSCORE = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_rolling_zscore(col, window, min_periods) {
        /*
        使用窗口均值和标准差计算当前值的 z-score。

        窗口右对齐，当前位置使用当前观测及其前 window - 1 个观测。min_periods 为 NULL 时等于 window；有效观测不足时返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        window : int
            正整数窗口长度。窗口包含当前位置以及此前 window - 1 个观测。
        min_periods : int or NULL, default NULL
            窗口内产生结果所需的最少非 NULL 观测数。NULL 表示使用 window；必须满足 1 <= min_periods <= window。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：均值和标准差跳过窗口内 NULL；当前位置为 NULL 或窗口标准差为 0 时结果为 NULL。

        窗口边界：窗口右对齐并包含当前位置；min_periods 为 NULL 时要求完整 window
        个有效观测，window 和 min_periods 均按观测行数而非日期跨度解释。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        min_periods=NULL 时要求完整窗口：
        >>> ts_unary_rolling_zscore(col, 3, int(NULL))
        [NULL, NULL, 1.09109, 0, 1, 1, 0, 1]

        min_periods=1 时首个有效观测即可产生结果：
        >>> ts_unary_rolling_zscore(col, 3, 1)
        [NULL, 0.707107, 1.09109, 0, 1, 1, 0, 1]

        min_periods=2：
        >>> ts_unary_rolling_zscore(col, 3, 2)
        [NULL, 0.707107, 1.09109, 0, 1, 1, 0, 1]

        扩大到 4 期窗口：
        >>> ts_unary_rolling_zscore(col, 4, 2)
        [NULL, 0.707107, 1.09109, 0.387298, 1.1619, 1.31747, 0.439155, 1.1619]
        */
        minimum = rolling_min_periods(window, min_periods)
        scale = mstd(col, int(window), minimum)
        return iif(scale == 0, NULL, (col - mavg(col, int(window), minimum)) / scale)
    }
    """,
    dependencies=(ROLLING_MIN_PERIODS,)
)

TS_UNARY_SHIFT = DolphinDBFunction(
    module="query",
    definition="""
    def ts_unary_shift(col, periods) {
        /*
        把序列按指定观测期数位移。

        periods 按观测条数而不是自然日计数。没有足够历史观测的位置返回 NULL。

        Parameters
        ----------
        col : vector
            按时间升序排列的输入向量。
        periods : int, default 1
            位移的观测期数；正数读取历史观测，负数读取未来观测，0 返回原值。

        Returns
        -------
        result : vector[NUMBER]
            与输入序列等长；历史观测不足或计算无定义的位置为 NULL。

        Notes
        -----
        NULL 处理：原序列中的 NULL 随位移移动；移出边界的位置丢弃，移入边界的空位使用 typed NULL。

        位置语义：periods 按观测位置而非自然日移动，不跳过 NULL，也不按日期间隔补齐缺失交易日。

        Examples
        --------
        >>> col = 1.0 2.0 4.0 3.0 5.0 7.0 6.0 8.0

        periods=1：
        >>> ts_unary_shift(col, 1)
        [NULL, 1, 2, 4, 3, 5, 7, 6]

        periods=2：
        >>> ts_unary_shift(col, 2)
        [NULL, NULL, 1, 2, 4, 3, 5, 7]

        periods=3：
        >>> ts_unary_shift(col, 3)
        [NULL, NULL, NULL, 1, 2, 4, 3, 5]
        */
        return move(col, int(periods))
    }
    """
)

TIME_SERIES_OPERATOR_FUNCTIONS = (
    TS_BINARY_CROSS_ABOVE,
    TS_BINARY_CROSS_BELOW,
    TS_BINARY_EWM_CORR,
    TS_BINARY_EWM_COV,
    TS_BINARY_EXPANDING_BETA,
    TS_BINARY_EXPANDING_CORR,
    TS_BINARY_EXPANDING_COV,
    TS_BINARY_ROLLING_ALPHA,
    TS_BINARY_ROLLING_BETA,
    TS_BINARY_ROLLING_CORR,
    TS_BINARY_ROLLING_COV,
    TS_BINARY_ROLLING_RESIDUAL,
    TS_CONTROLS_ROLLING_ALPHA,
    TS_CONTROLS_ROLLING_BETA,
    TS_CONTROLS_ROLLING_RESIDUAL,
    TS_TALIB_AD,
    TS_TALIB_ADX,
    TS_TALIB_ADXR,
    TS_TALIB_APO,
    TS_TALIB_AROON,
    TS_TALIB_AROONOSC,
    TS_TALIB_ATR,
    TS_TALIB_AVGPRICE,
    TS_TALIB_BBANDS,
    TS_TALIB_BETA,
    TS_TALIB_BOP,
    TS_TALIB_CCI,
    TS_TALIB_CORREL,
    TS_TALIB_DEMA,
    TS_TALIB_DX,
    TS_TALIB_EMA,
    TS_TALIB_KAMA,
    TS_TALIB_LINEARREG,
    TS_TALIB_LINEARREG_ANGLE,
    TS_TALIB_LINEARREG_INTERCEPT,
    TS_TALIB_LINEARREG_SLOPE,
    TS_TALIB_MA,
    TS_TALIB_MACD,
    TS_TALIB_MEDPRICE,
    TS_TALIB_MFI,
    TS_TALIB_MIDPOINT,
    TS_TALIB_MIDPRICE,
    TS_TALIB_MINUS_DI,
    TS_TALIB_MINUS_DM,
    TS_TALIB_MOM,
    TS_TALIB_NATR,
    TS_TALIB_OBV,
    TS_TALIB_PLUS_DI,
    TS_TALIB_PLUS_DM,
    TS_TALIB_PPO,
    TS_TALIB_ROC,
    TS_TALIB_ROCP,
    TS_TALIB_ROCR,
    TS_TALIB_ROCR100,
    TS_TALIB_RSI,
    TS_TALIB_SMA,
    TS_TALIB_STDDEV,
    TS_TALIB_T3,
    TS_TALIB_TEMA,
    TS_TALIB_TRANGE,
    TS_TALIB_TRIMA,
    TS_TALIB_TRIX,
    TS_TALIB_TSF,
    TS_TALIB_TYPPRICE,
    TS_TALIB_ULTOSC,
    TS_TALIB_VAR,
    TS_TALIB_WCLPRICE,
    TS_TALIB_WILLR,
    TS_TALIB_WMA,
    TS_UNARY_BARS_SINCE,
    TS_UNARY_BFILL,
    TS_UNARY_CHANGED,
    TS_UNARY_CONSECUTIVE_COUNT,
    TS_UNARY_CUM_COUNT,
    TS_UNARY_CUM_MAX,
    TS_UNARY_CUM_MEAN,
    TS_UNARY_CUM_MIN,
    TS_UNARY_CUM_PROD,
    TS_UNARY_CUM_SUM,
    TS_UNARY_DECAY_LINEAR,
    TS_UNARY_DIFF,
    TS_UNARY_EWM_MEAN,
    TS_UNARY_EWM_STD,
    TS_UNARY_EWM_VAR,
    TS_UNARY_EXPANDING_MEDIAN,
    TS_UNARY_EXPANDING_QUANTILE,
    TS_UNARY_EXPANDING_RANK,
    TS_UNARY_EXPANDING_RANK_PCT,
    TS_UNARY_EXPANDING_SEM,
    TS_UNARY_EXPANDING_STD,
    TS_UNARY_EXPANDING_VAR,
    TS_UNARY_FFILL,
    TS_UNARY_LOG_RETURN,
    TS_UNARY_PCT_CHANGE,
    TS_UNARY_ROLLING_ALL,
    TS_UNARY_ROLLING_ANY,
    TS_UNARY_ROLLING_ARGMAX,
    TS_UNARY_ROLLING_ARGMIN,
    TS_UNARY_ROLLING_COUNT,
    TS_UNARY_ROLLING_FIRST,
    TS_UNARY_ROLLING_KURT,
    TS_UNARY_ROLLING_LAST,
    TS_UNARY_ROLLING_MAD,
    TS_UNARY_ROLLING_MAX,
    TS_UNARY_ROLLING_MEAN,
    TS_UNARY_ROLLING_MEDIAN,
    TS_UNARY_ROLLING_MIN,
    TS_UNARY_ROLLING_PROD,
    TS_UNARY_ROLLING_QUANTILE,
    TS_UNARY_ROLLING_RANK,
    TS_UNARY_ROLLING_RANK_PCT,
    TS_UNARY_ROLLING_SEM,
    TS_UNARY_ROLLING_SKEW,
    TS_UNARY_ROLLING_STD,
    TS_UNARY_ROLLING_SUM,
    TS_UNARY_ROLLING_TRUE_COUNT,
    TS_UNARY_ROLLING_VAR,
    TS_UNARY_ROLLING_ZSCORE,
    TS_UNARY_SHIFT,
)
