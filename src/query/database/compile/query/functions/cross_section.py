"""截面算符的 DolphinDB 实现。"""

from query.database.compile import DolphinDBFunction
from query.database.compile.common.functions import (
    BROADCAST_LIKE,
    CONTROLS_REGRESSION,
    CROSS_SECTION_RANK,
    CROSS_SECTION_SLOPE,
)

CS_BINARY_ALPHA = DolphinDBFunction(
    module="query",
    definition="""
    def cs_binary_alpha(left, right) {
        /*
        在当前截面回归 right 对 left，并把截距项广播到整个截面。

        回归方向固定为 right 对 left：right 是因变量，left 是解释变量。斜率为 Cov(left, right) / Var(left)，截距为
        pairMean(right) - beta * pairMean(left)，其中两个均值只使用同一组成对有效观测。

        协方差按成对有效观测计算。left 没有有效截面方差时斜率为 NULL，依赖该斜率的结果也为 NULL。

        Parameters
        ----------
        left : vector
            回归中的解释变量向量。
        right : vector
            回归中的因变量向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：回归系数只使用 left 与 right 同时非 NULL 的配对观测，有效配对不足时统计量为
        NULL。

        计算边界：先计算 beta，再使用成对有效样本的均值计算截距，并将截距广播到整个截面。

        Examples
        --------
        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> cs_binary_alpha(left, right)
        [-0.01, -0.01, -0.01, -0.01, -0.01]

        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> left[1] = NULL
        >>> right[3] = NULL

        成对忽略缺失观测：
        >>> cs_binary_alpha(left, right)
        [0.133333, 0.133333, 0.133333, 0.133333, 0.133333]

        >>> left = 1.0 1.0 1.0 1.0
        >>> right = 2.0 3.0 4.0 5.0

        解释变量无截面方差时返回 NULL：
        >>> cs_binary_alpha(left, right)
        [NULL, NULL, NULL, NULL]
        */
        valid = isValid(left) && isValid(right)
        paired_left = iif(valid, double(left), double(NULL))
        paired_right = iif(valid, double(right), double(NULL))
        slope = cross_section_slope(left, right)
        return broadcast_like(avg(paired_right) - slope * avg(paired_left), left)
    }
    """,
    dependencies=(BROADCAST_LIKE, CROSS_SECTION_SLOPE)
)

CS_BINARY_BETA = DolphinDBFunction(
    module="query",
    definition="""
    def cs_binary_beta(left, right) {
        /*
        在当前截面回归 right 对 left，并把斜率项广播到整个截面。

        回归方向固定为 right 对 left：right 是因变量，left 是解释变量。斜率为 Cov(left, right) / Var(left)；
        协方差和方差均只使用 left 与 right 同时有效的同一组观测。

        协方差按成对有效观测计算。left 没有有效截面方差时斜率为 NULL，依赖该斜率的结果也为 NULL。

        Parameters
        ----------
        left : vector
            回归中的解释变量向量。
        right : vector
            回归中的因变量向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：回归系数只使用 left 与 right 同时非 NULL 的配对观测，有效配对不足时统计量为
        NULL。

        计算边界：beta 的分母是 left 的截面方差，零方差时结果为 NULL 并广播。

        Examples
        --------
        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> cs_binary_beta(left, right)
        [2.01, 2.01, 2.01, 2.01, 2.01]

        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> left[1] = NULL
        >>> right[3] = NULL

        成对忽略缺失观测：
        >>> cs_binary_beta(left, right)
        [2, 2, 2, 2, 2]

        >>> left = 1.0 1.0 1.0 1.0
        >>> right = 2.0 3.0 4.0 5.0

        解释变量无截面方差时返回 NULL：
        >>> cs_binary_beta(left, right)
        [NULL, NULL, NULL, NULL]
        */
        return broadcast_like(cross_section_slope(left, right), left)
    }
    """,
    dependencies=(BROADCAST_LIKE, CROSS_SECTION_SLOPE)
)

CS_BINARY_CORR = DolphinDBFunction(
    module="query",
    definition="""
    def cs_binary_corr(left, right) {
        /*
        计算当前截面两个向量的 Pearson 相关系数并广播结果。

        统计量只使用 left 与 right 的成对有效观测，并把单个截面统计值广播到所有输出位置。

        Parameters
        ----------
        left : vector
            Pearson 相关系数的第一条截面数值向量。
        right : vector
            与 left 成对观测的第二条截面数值向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：只使用 left 与 right 同时非 NULL 的配对观测，有效配对不足时统计量为 NULL。

        计算边界：相关系数在任一侧零方差时无定义；标量结果广播到整个截面。

        Examples
        --------
        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> cs_binary_corr(left, right)
        [0.998678, 0.998678, 0.998678, 0.998678, 0.998678]

        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> left[1] = NULL
        >>> right[3] = NULL

        成对忽略缺失观测：
        >>> cs_binary_corr(left, right)
        [0.999896, 0.999896, 0.999896, 0.999896, 0.999896]
        */
        return broadcast_like(corr(left, right), left)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_BINARY_COV = DolphinDBFunction(
    module="query",
    definition="""
    def cs_binary_cov(left, right) {
        /*
        计算当前截面两个向量的样本协方差并广播结果。

        统计量只使用 left 与 right 的成对有效观测，并把单个截面统计值广播到所有输出位置。

        Parameters
        ----------
        left : vector
            截面协方差的第一条数值向量。
        right : vector
            与 left 成对观测的第二条截面数值向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：只使用 left 与 right 同时非 NULL 的配对观测，有效配对不足时统计量为 NULL。

        计算边界：使用 DolphinDB 截面协方差口径；标量结果广播到整个截面。

        Examples
        --------
        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> cs_binary_cov(left, right)
        [5.025, 5.025, 5.025, 5.025, 5.025]

        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> left[1] = NULL
        >>> right[3] = NULL

        成对忽略缺失观测：
        >>> cs_binary_cov(left, right)
        [8, 8, 8, 8, 8]
        */
        return broadcast_like(covar(left, right), left)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_BINARY_RANK_CORR = DolphinDBFunction(
    module="query",
    definition="""
    def cs_binary_rank_corr(left, right) {
        /*
        对两个向量的成对有效观测分别排名，再计算当前截面的 Pearson 相关系数。

        先排除任一侧为 NULL 的观测，再分别排名并计算 Pearson 相关系数，因此结果等价于
        使用成对完整样本计算的 Spearman 相关系数。

        相关系数是标量，并广播为与 left 等长的向量。

        Parameters
        ----------
        left : vector
            先转换为排名的第一条截面数值向量。
        right : vector
            与 left 成对排名的第二条截面数值向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：先排除 left 或 right 为 NULL 的整条观测，再对同一批有效样本分别排名；
        有效配对不足时统计量为 NULL。

        计算边界：并列值使用平均秩，与 Spearman 定义一致；秩相关系数广播到整个截面。

        Examples
        --------
        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> cs_binary_rank_corr(left, right)
        [1, 1, 1, 1, 1]

        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> left[1] = NULL
        >>> right[3] = NULL

        成对忽略缺失观测：
        >>> cs_binary_rank_corr(left, right)
        [1, 1, 1, 1, 1]
        */
        valid = isValid(left) && isValid(right)
        if (sum(valid) < 2) return take(double(NULL), size(left))
        value = corr(rank(left[valid], true, , true, `average, false),
                     rank(right[valid], true, , true, `average, false))
        return broadcast_like(value, left)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_BINARY_RESIDUAL = DolphinDBFunction(
    module="query",
    definition="""
    def cs_binary_residual(left, right) {
        /*
        在当前截面回归 right 对 left，返回每个观测对应的残差。

        回归方向固定为 right 对 left：right 是因变量，left 是解释变量。斜率为 Cov(left, right) / Var(left)，截距为
        pairMean(right) - beta * pairMean(left)，其中两个均值只使用同一组成对有效观测。

        协方差按成对有效观测计算。left 没有有效截面方差时斜率为 NULL，依赖该斜率的结果也为 NULL。

        Parameters
        ----------
        left : vector
            回归中的解释变量向量。
        right : vector
            回归中的因变量向量。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：回归系数只使用 left 与 right 同时非 NULL 的配对观测，有效配对不足时统计量为
        NULL。

        计算边界：逐行返回 right 对 left 的 OLS 残差；任一当前输入缺失或 left 零方差时相应残差为
        NULL。

        Examples
        --------
        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> cs_binary_residual(left, right)
        [0.1, -0.21, 0.18, -0.13, 0.06]

        >>> left = 1.0 2.0 3.0 4.0 5.0
        >>> right = 2.1 3.8 6.2 7.9 10.1
        >>> left[1] = NULL
        >>> right[3] = NULL

        成对忽略缺失观测：
        >>> cs_binary_residual(left, right)
        [-0.033333, NULL, 0.066667, NULL, -0.033333]

        >>> left = 1.0 1.0 1.0 1.0
        >>> right = 2.0 3.0 4.0 5.0

        解释变量无截面方差时返回 NULL：
        >>> cs_binary_residual(left, right)
        [NULL, NULL, NULL, NULL]
        */
        valid = isValid(left) && isValid(right)
        paired_left = iif(valid, double(left), double(NULL))
        paired_right = iif(valid, double(right), double(NULL))
        slope = cross_section_slope(left, right)
        intercept = avg(paired_right) - slope * avg(paired_left)
        return right - intercept - slope * left
    }
    """,
    dependencies=(CROSS_SECTION_SLOPE,)
)

CS_CONTROLS_ALPHA = DolphinDBFunction(
    module="query",
    definition=r"""
    def cs_controls_alpha(target, controls, intercept) {
        /*
        用连续、BOOL、STRING、SYMBOL 控制变量解释 target，返回截面截距。

        Parameters
        ----------
        target : vector[NUMBER]
            当前截面的数值因变量。
        controls : table
            同行数的有序控制列；分类列独热编码后去掉最小类别，常量列不拟合。
        intercept : bool
            正常拟合是否包含截距；false 时正常拟合返回 0。

        Returns
        -------
        result : vector[NUMBER]
            与 target 等长；共同有效行广播同一个截距，其余行保持 NULL。

        Notes
        -----
        共同排除缺失、非有限数值；无控制或样本不足沿用去均值退化，返回 avg(y)。
        不执行前向填充、去极值或标准化；分类编码只使用本截面的有效样本。

        Examples
        --------
        >>> cs_controls_alpha(1.0 2.2 2.8 4.1 4.9, table(8.0 9 10 11 12 as size), true)
        [-6.7, -6.7, -6.7, -6.7, -6.7]
        */
        fit = controls_regression(target, controls, intercept)
        return iif(fit.valid, fit.alpha, double(NULL))
    }
    """,
    dependencies=(CONTROLS_REGRESSION,),
)

CS_CONTROLS_BETA = DolphinDBFunction(
    module="query",
    definition=r"""
    def cs_controls_beta(target, controls, intercept, index) {
        /*
        用有序的连续或分类控制列解释 target，返回指定展开列的截面回归系数。

        Parameters
        ----------
        target : vector[NUMBER]
            当前截面的数值因变量。
        controls : table
            同行数的解释变量；按列顺序展开，分类列按类别值排序删除首类。
        intercept : bool
            正常拟合是否包含截距。
        index : int
            0 起算的展开列位置，不包含截距；数值常量列保留位置并返回 0。
            分类类别和基准以当前截面为准，因此动态类别的索引需由调用方确认。

        Returns
        -------
        result : vector[NUMBER]
            共同有效行广播指定系数，无效行或该截面不存在的展开列为 NULL。

        Notes
        -----
        缺失规则与 controls.residual 一致；退化到去均值时已有系数位置返回 0。
        index<0 或非整数报错，不把类别字符串当连续数字。

        Examples
        --------
        >>> cs_controls_beta(1.0 2.2 2.8 4.1 4.9, table(8.0 9 10 11 12 as size), true, 0)
        [0.97, 0.97, 0.97, 0.97, 0.97]
        */
        if (isNull(index) || index < 0 || index != int(index)) throw "回归系数 index 必须是非负整数"
        fit = controls_regression(target, controls, intercept)
        if (index >= size(fit.beta)) return take(double(NULL), size(target))
        return iif(fit.valid, fit.beta[int(index)], double(NULL))
    }
    """,
    dependencies=(CONTROLS_REGRESSION,),
)

CS_CONTROLS_RESIDUAL = DolphinDBFunction(
    module="query",
    definition=r"""
    def cs_controls_residual(target, controls, intercept) {
        /*
        以连续或分类控制变量做截面 OLS，返回各共同有效观测的残差。

        Parameters
        ----------
        target : vector[NUMBER]
            需要解释的数值目标。
        controls : table
            与目标等行数的控制表；BOOL、STRING、SYMBOL 独热编码，去首类。
        intercept : bool
            正常回归是否包含截距。

        Returns
        -------
        result : vector[NUMBER]
            与 target 等长；无效行保留 NULL，正常行返回 y-alpha-X*beta。

        Notes
        -----
        完全替换旧中性化名称，不提供旧算符或 DOS 函数别名。
        沿用分类基准删除、常量控制删除和小样本去均值规则，不补 NULL。
        不自动取对数、去极值、标准化，也不是 Scheme 完整因子预处理。

        Examples
        --------
        >>> cs_controls_residual(1.0 3 2 6 4 8, table(`bank`bank`tech`tech`retail`retail as industry), true)
        [-1, 1, -2, 2, -2, 2]
        >>> cs_controls_residual(1.0 2 4 8, table(take(1.0,4) as constant), true)
        [-2.75, -1.75, 0.25, 4.25]
        */
        return controls_regression(target, controls, intercept).residual
    }
    """,
    dependencies=(CONTROLS_REGRESSION,),
)

CS_GROUPED_DEMEAN = DolphinDBFunction(
    module="query",
    definition="""
    def cs_grouped_demean(col) {
        /*
        在当前分类组内减去组均值。

        计算只使用传入的当前分类组，返回向量与 col 等长。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：组均值忽略 NULL，但减法会保留原输入的 NULL，因此缺失位置的结果仍为 NULL。

        分组内语义：每组只减去本组均值，不使用其他组观测，也不做尺度标准化。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_grouped_demean(col)
        [-2.4, -1.4, -1.4, 0.6, 4.6]

        均值跳过 NULL，但缺失位置仍缺失：
        >>> cs_grouped_demean(double([1, NULL, 3]))
        [-1, NULL, 1]
        */
        return col - avg(col)
    }
    """
)

CS_GROUPED_MEAN = DolphinDBFunction(
    module="query",
    definition="""
    def cs_grouped_mean(col) {
        /*
        计算当前分类组的均值，并把该值广播到组内各观测。

        计算只使用传入的当前分类组，返回向量与 col 等长。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：组均值忽略 NULL，并把同一均值广播到组内全部位置，包括原输入为 NULL
        的位置；整组无有效值时返回 NULL。

        分组内语义：每组均值独立计算并广播，不使用其他组观测。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_grouped_mean(col)
        [3.4, 3.4, 3.4, 3.4, 3.4]

        均值会广播到原缺失位置：
        >>> cs_grouped_mean(double([1, NULL, 3]))
        [2, 2, 2]
        */
        return broadcast_like(avg(col), col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_GROUPED_RANK_PCT = DolphinDBFunction(
    module="query",
    definition="""
    def cs_grouped_rank_pct(col, ascending, ties_method) {
        /*
        在当前分类组内计算百分位排名。

        结果位于 (0, 1]；并列值如何分配百分位由 ties_method 决定。NULL 不参与有效样本排名。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        ascending : bool, default true
            true 时最小值排名最前；false 时最大值排名最前。
        ties_method : {"min", "max", "average", "first", "dense"}, default "min"
            并列值处理方式：
            * "min"：并列组使用该组的最小名次。
            * "max"：并列组使用该组的最大名次。
            * "average"：并列组使用所占名次的平均值。
            * "first"：按输入中的出现顺序为并列值分配不同名次。
            * "dense"：类似 "min"，但下一组名次只增加 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：排名忽略 NULL，缺失输入位置的排名仍为 NULL；百分位分母只包含有效值。

        分组内语义：ascending 和 ties_method 在每组独立应用，百分位分母只计有效值。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        ties_method="min"：
        >>> cs_grouped_rank_pct(col, true, "min")
        [0.2, 0.4, 0.4, 0.8, 1]

        ties_method="max"：
        >>> cs_grouped_rank_pct(col, true, "max")
        [0.2, 0.6, 0.6, 0.8, 1]

        ties_method="average"：
        >>> cs_grouped_rank_pct(col, true, "average")
        [0.2, 0.5, 0.5, 0.8, 1]

        ties_method="first"：
        >>> cs_grouped_rank_pct(col, true, "first")
        [0.2, 0.4, 0.6, 0.8, 1]

        ties_method="dense"：
        >>> cs_grouped_rank_pct(col, true, "dense")
        [0.25, 0.5, 0.5, 0.75, 1]

        降序排名：
        >>> cs_grouped_rank_pct(col, false, "min")
        [1, 0.6, 0.6, 0.4, 0.2]
        */
        return cross_section_rank(col, ascending, ties_method, true)
    }
    """,
    dependencies=(CROSS_SECTION_RANK,)
)

CS_GROUPED_ZSCORE = DolphinDBFunction(
    module="query",
    definition="""
    def cs_grouped_zscore(col, ddof) {
        /*
        在当前分类组内计算 z-score。

        标准化使用 (x - mean) / std。组内标准差为 0 或无法计算时，整个组返回 NULL。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        ddof : {0, 1}, default 1
            自由度修正。0 使用总体统计量，分母为 N；1 使用样本统计量，分母为 N - 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：组均值和标准差忽略 NULL，缺失输入位置仍返回 NULL；有效标准差为 0 或无法按 ddof
        估计时，整组结果为 NULL。

        分组内语义：ddof 在每组独立应用；组内有效样本不足或尺度为 0 时返回 NULL。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        总体统计口径，ddof=0：
        >>> cs_grouped_zscore(col, 0)
        [-0.960769, -0.560449, -0.560449, 0.240192, 1.84147]

        样本统计口径，ddof=1：
        >>> cs_grouped_zscore(col, 1)
        [-0.859338, -0.50128, -0.50128, 0.214834, 1.64706]
        */
        scale = iif(int(ddof) == 0, stdp(col), std(col))
        if (isNull(scale) || scale == 0) return take(double(NULL), size(col))
        return (col - avg(col)) / scale
    }
    """
)

CS_UNARY_BOTTOM_N = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_bottom_n(col, n) {
        /*
        标记当前截面中数值最小的 n 个有效观测。

        选择结果为布尔向量。并列值按原始出现顺序打破平局，使最终入选数量可确定。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        n : int
            需要标记的有效观测数量，必须至少为 1。

        Returns
        -------
        result : vector[BOOL]
            与 col 等长的 BOOL 选择标记。

        Notes
        -----
        NULL 处理：排名只使用非 NULL 观测，原输入为 NULL 的位置明确返回
        false，不会占用顶部或底部的选择名额。全 NULL 截面返回全 false。

        选择边界：按升序选择最多 n 个有效观测；n 超过有效样本数时全体有效值入选。并列值以 first
        规则按原顺序打破。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        选择 1 个观测：
        >>> cs_unary_bottom_n(col, 1)
        [true, false, false, false, false]

        选择 2 个观测：
        >>> cs_unary_bottom_n(col, 2)
        [true, true, false, false, false]

        选择 3 个观测：
        >>> cs_unary_bottom_n(col, 3)
        [true, true, true, false, false]
        */
        return !isNull(col) && (rank(col, true, , true, `first, false) < int(n))
    }
    """
)

CS_UNARY_BOTTOM_PCT = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_bottom_pct(col, pct) {
        /*
        标记当前截面中位于底部指定比例的有效观测。

        选择结果为布尔向量。并列值按原始出现顺序打破平局，使最终入选数量可确定。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        pct : float
            需要标记的有效观测比例，取值范围为 (0, 1]；数量向上取整。

        Returns
        -------
        result : vector[BOOL]
            与 col 等长的 BOOL 选择标记。

        Notes
        -----
        NULL 处理：排名只使用非 NULL 观测，原输入为 NULL 的位置明确返回
        false，不会占用顶部或底部的选择名额。全 NULL 截面返回全 false。

        选择边界：按升序选择 ceil(有效样本数 * pct) 个观测。并列值以 first 规则按原顺序打破。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        选择 20%：
        >>> cs_unary_bottom_pct(col, 0.2)
        [true, false, false, false, false]

        选择 40%：
        >>> cs_unary_bottom_pct(col, 0.4)
        [true, true, false, false, false]

        选择 60%：
        >>> cs_unary_bottom_pct(col, 0.6)
        [true, true, true, false, false]
        */
        return !isNull(col) && (rank(col, true, , true, `first, false) < ceil(count(col) * pct))
    }
    """
)

CS_UNARY_COUNT = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_count(col) {
        /*
        统计当前截面的非 NULL 观测数并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：只统计非 NULL 值，并把计数广播到截面全部位置；全 NULL 截面返回 0。

        输出形状：结果与输入等长，每个位置保存相同统计量。输出为有效观测数量的整数广播向量，而不是逐元素有效性标记。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_count(col)
        [5, 5, 5, 5, 5]

        只统计有效观测并广播：
        >>> cs_unary_count(double([1, NULL, 3]))
        [2, 2, 2]
        */
        return broadcast_like(count(col), col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_DEMEAN = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_demean(col) {
        /*
        从每个有效观测中减去当前截面均值。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面均值忽略 NULL，但原输入为 NULL 的位置在减法后仍为 NULL；全 NULL
        截面没有可用均值。

        数值语义：只移除截面均值，不除以尺度；有效残差之和仅受浮点舍入误差影响，理论上为 0。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_demean(col)
        [-2.4, -1.4, -1.4, 0.6, 4.6]

        均值跳过 NULL，但缺失位置仍缺失：
        >>> cs_unary_demean(double([1, NULL, 3]))
        [-1, NULL, 1]
        */
        return col - avg(col)
    }
    """
)

CS_UNARY_KURT = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_kurt(col) {
        /*
        计算当前截面的峰度并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面统计忽略 NULL，并把单个统计量广播到截面全部位置，包括原输入为 NULL
        的位置；没有足够有效样本时广播 NULL。

        输出形状：结果与输入等长，每个位置保存相同统计量。输出为截面峰度的广播向量，而不是逐元素变换。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_kurt(col)
        [2.51036, 2.51036, 2.51036, 2.51036, 2.51036]

        有效样本足够时，NULL 不阻断截面统计：
        >>> all(!isNull(cs_unary_kurt(double([1, NULL, 2, 3, 4, 5]))))
        true
        */
        return broadcast_like(kurtosis(col), col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_MAD = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_mad(col) {
        /*
        计算当前截面的中位数绝对离差（MAD）并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面统计忽略 NULL，并把单个统计量广播到截面全部位置，包括原输入为 NULL
        的位置；没有足够有效样本时广播 NULL。

        输出形状：结果与输入等长，每个位置保存相同统计量。输出为截面中位数绝对偏差的广播向量，而不是逐元素变换。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_mad(col)
        [1, 1, 1, 1, 1]

        有效样本足够时，NULL 不阻断截面统计：
        >>> all(!isNull(cs_unary_mad(double([1, NULL, 2, 3, 4, 5]))))
        true
        */
        return broadcast_like(mad(col, true), col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_MAX = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_max(col) {
        /*
        计算当前截面的最大值并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面统计忽略 NULL，并把单个统计量广播到截面全部位置，包括原输入为 NULL
        的位置；没有足够有效样本时广播 NULL。

        输出形状：结果与输入等长，每个位置保存相同统计量。输出为截面最大值的广播向量，而不是逐元素变换。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_max(col)
        [8, 8, 8, 8, 8]

        最大值跳过 NULL 并广播：
        >>> cs_unary_max(double([1, NULL, 3]))
        [3, 3, 3]
        */
        return broadcast_like(max(col), col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_MEAN = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_mean(col) {
        /*
        计算当前截面的算术平均值并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面统计忽略 NULL，并把单个统计量广播到截面全部位置，包括原输入为 NULL
        的位置；没有足够有效样本时广播 NULL。

        输出形状：结果与输入等长，每个位置保存相同统计量。输出为截面算术平均值的广播向量，而不是逐元素变换。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_mean(col)
        [3.4, 3.4, 3.4, 3.4, 3.4]

        均值会广播到原缺失位置：
        >>> cs_unary_mean(double([1, NULL, 3]))
        [2, 2, 2]
        */
        return broadcast_like(avg(col), col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_MEDIAN = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_median(col) {
        /*
        计算当前截面的中位数并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面统计忽略 NULL，并把单个统计量广播到截面全部位置，包括原输入为 NULL
        的位置；没有足够有效样本时广播 NULL。

        输出形状：结果与输入等长，每个位置保存相同统计量。输出为截面中位数的广播向量，而不是逐元素变换。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_median(col)
        [2, 2, 2, 2, 2]

        中位数跳过 NULL 并广播：
        >>> cs_unary_median(double([1, NULL, 3]))
        [2, 2, 2]
        */
        return broadcast_like(med(col), col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_MIN = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_min(col) {
        /*
        计算当前截面的最小值并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面统计忽略 NULL，并把单个统计量广播到截面全部位置，包括原输入为 NULL
        的位置；没有足够有效样本时广播 NULL。

        输出形状：结果与输入等长，每个位置保存相同统计量。输出为截面最小值的广播向量，而不是逐元素变换。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_min(col)
        [1, 1, 1, 1, 1]

        最小值跳过 NULL 并广播：
        >>> cs_unary_min(double([1, NULL, 3]))
        [1, 1, 1]
        */
        return broadcast_like(min(col), col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_NORMALIZE_L1 = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_normalize_l1(col) {
        /*
        用绝对值之和缩放当前截面，使 L1 范数为 1。

        分母为当前截面的绝对值之和。分母为 0 或 NULL 时整个结果返回 NULL；原输入中的 NULL 位置保持 NULL。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：分母按有效值绝对值之和计算并忽略 NULL，原输入为 NULL 的位置仍为 NULL；分母为 0
        或无有效值时整个截面返回 NULL。

        归一化语义：有效结果的绝对值之和为 1，不执行中心化。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_normalize_l1(col)
        [0.0588235, 0.117647, 0.117647, 0.235294, 0.470588]

        分母忽略 NULL，缺失位置保持 NULL：
        >>> cs_unary_normalize_l1(double([1, NULL, 3]))
        [0.25, NULL, 0.75]
        */
        denominator = sum(abs(col))
        if (isNull(denominator) || denominator == 0) return take(double(NULL), size(col))
        return col / denominator
    }
    """
)

CS_UNARY_NORMALIZE_L2 = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_normalize_l2(col) {
        /*
        用平方和的平方根缩放当前截面，使 L2 范数为 1。

        分母为当前截面的平方和的平方根。分母为 0 或 NULL 时整个结果返回 NULL；原输入中的 NULL 位置保持 NULL。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：分母按有效值平方和的平方根计算并忽略 NULL，原输入为 NULL 的位置仍为 NULL；分母为 0
        或无有效值时整个截面返回 NULL。

        归一化语义：有效结果的平方和为 1，不执行中心化。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_normalize_l2(col)
        [0.106, 0.212, 0.212, 0.423999, 0.847998]

        分母忽略 NULL，缺失位置保持 NULL：
        >>> isNull(cs_unary_normalize_l2(double([1, NULL, 3])))
        [false, true, false]
        */
        denominator = sqrt(sum(col * col))
        if (isNull(denominator) || denominator == 0) return take(double(NULL), size(col))
        return col / denominator
    }
    """
)

CS_UNARY_NORMALIZE_SUM = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_normalize_sum(col) {
        /*
        用总和缩放当前截面，使有效值之和为 1。

        分母为当前截面的有效值总和。分母为 0 或 NULL 时整个结果返回 NULL；原输入中的 NULL 位置保持 NULL。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：分母按有效值之和计算并忽略 NULL，原输入为 NULL 的位置仍为 NULL；分母为 0
        或无有效值时整个截面返回 NULL。

        归一化语义：正负值可能相互抵消，因此存在非零观测时总和仍可能为 0。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_normalize_sum(col)
        [0.0588235, 0.117647, 0.117647, 0.235294, 0.470588]

        分母忽略 NULL，缺失位置保持 NULL：
        >>> cs_unary_normalize_sum(double([1, NULL, 3]))
        [0.25, NULL, 0.75]
        */
        denominator = sum(col)
        if (isNull(denominator) || denominator == 0) return take(double(NULL), size(col))
        return col / denominator
    }
    """
)

CS_UNARY_QCUT = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_qcut(col, q) {
        /*
        按当前截面分位数把有效观测划分为 q 个整数分箱。

        分箱编号从 0 开始，最大为 q - 1。并列值使用最小名次，因此相同值不会被拆到不同分箱。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        q : int
            分箱数量，必须至少为 2；返回编号范围为 0 到 q - 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：分箱只使用非 NULL 观测，原输入为 NULL 的位置返回
        NULL；有效样本数量决定可形成的分箱。

        排名语义：按有效值排名后划分 q 个整数分箱；有效样本过少时部分箱可能为空。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        划分为 2 箱：
        >>> cs_unary_qcut(col, 2)
        [0, 0, 0, 1, 1]

        划分为 3 箱：
        >>> cs_unary_qcut(col, 3)
        [0, 0, 0, 1, 2]

        划分为 4 箱：
        >>> cs_unary_qcut(col, 4)
        [0, 0, 0, 2, 3]
        */
        return rank(col, true, int(q), true, `min, false)
    }
    """
)

CS_UNARY_QUANTILE = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_quantile(col, q) {
        /*
        计算当前截面的指定分位数并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        q : float
            目标分位数，取值范围为 [0, 1]。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面统计忽略 NULL，并把单个统计量广播到截面全部位置，包括原输入为 NULL
        的位置；没有足够有效样本时广播 NULL。

        输出形状：结果与输入等长，每个位置保存相同统计量。q 指定截面分位点；结果是该分位数广播后的向量。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        q=0.25：
        >>> cs_unary_quantile(col, 0.25)
        [2, 2, 2, 2, 2]

        q=0.5：
        >>> cs_unary_quantile(col, 0.5)
        [2, 2, 2, 2, 2]

        q=0.75：
        >>> cs_unary_quantile(col, 0.75)
        [4, 4, 4, 4, 4]
        */
        return broadcast_like(quantile(col, q), col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_RANK = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_rank(col, ascending, ties_method) {
        /*
        计算当前截面的普通排名。

        NULL 不参与排名。普通排名从 1 开始；百分位排名位于 (0, 1]；密集排名在并列组之间不跳号。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        ascending : bool, default true
            true 时最小值排名最前；false 时最大值排名最前。
        ties_method : {"min", "max", "average", "first", "dense"}, default "min"
            并列值处理方式：
            * "min"：并列组使用该组的最小名次。
            * "max"：并列组使用该组的最大名次。
            * "average"：并列组使用所占名次的平均值。
            * "first"：按输入中的出现顺序为并列值分配不同名次。
            * "dense"：类似 "min"，但下一组名次只增加 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：排名忽略 NULL，原输入为 NULL 的位置返回 NULL。

        排名语义：rank 从 1 开始；ascending 控制方向，ties_method 控制并列值。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        ties_method="min"：
        >>> cs_unary_rank(col, true, "min")
        [1, 2, 2, 4, 5]

        ties_method="max"：
        >>> cs_unary_rank(col, true, "max")
        [1, 3, 3, 4, 5]

        ties_method="average"：
        >>> cs_unary_rank(col, true, "average")
        [1, 2.5, 2.5, 4, 5]

        ties_method="first"：
        >>> cs_unary_rank(col, true, "first")
        [1, 2, 3, 4, 5]

        ties_method="dense"：
        >>> cs_unary_rank(col, true, "dense")
        [1, 2, 2, 3, 4]

        降序排名：
        >>> cs_unary_rank(col, false, "min")
        [5, 3, 3, 2, 1]
        */
        return cross_section_rank(col, ascending, ties_method, false)
    }
    """,
    dependencies=(CROSS_SECTION_RANK,)
)

CS_UNARY_RANK_DENSE = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_rank_dense(col, ascending) {
        /*
        计算当前截面的密集排名，并列值使用相同名次且名次不跳号。

        NULL 不参与排名。普通排名从 1 开始；百分位排名位于 (0, 1]；密集排名在并列组之间不跳号。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        ascending : bool, default true
            true 时最小值排名最前；false 时最大值排名最前。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：排名忽略 NULL，原输入为 NULL 的位置返回 NULL。

        排名语义：密集排名从 1 开始，并列组之间不跳号；ascending 控制方向。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        升序密集排名：
        >>> cs_unary_rank_dense(col, true)
        [1, 2, 2, 3, 4]

        降序密集排名：
        >>> cs_unary_rank_dense(col, false)
        [4, 3, 3, 2, 1]
        */
        return cross_section_rank(col, ascending, "dense", false)
    }
    """,
    dependencies=(CROSS_SECTION_RANK,)
)

CS_UNARY_RANK_NORMAL = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_rank_normal(col, ascending) {
        /*
        把截面排名映射为标准正态分布分位数。

        先使用平均并列名次计算概率 (rank + 0.5) / n，再通过标准正态分布的逆累积分布函数映射。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        ascending : bool, default true
            true 时最小值排名最前；false 时最大值排名最前。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：排名忽略 NULL，原输入为 NULL 的位置返回 NULL。

        排名语义：先按 average ties 排名，再映射到标准正态分位数；ascending 控制方向。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        升序映射：
        >>> cs_unary_rank_normal(col, true)
        [-1.28155, -0.253347, -0.253347, 0.524401, 1.28155]

        降序映射：
        >>> cs_unary_rank_normal(col, false)
        [1.28155, 0.253347, 0.253347, -0.524401, -1.28155]
        */
        n = count(col)
        probability = (rank(col, ascending, , true, `average, false) + 0.5) / n
        return invNormal(0, 1, probability)
    }
    """
)

CS_UNARY_RANK_PCT = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_rank_pct(col, ascending, ties_method) {
        /*
        计算当前截面的百分位排名。

        NULL 不参与排名。普通排名从 1 开始；百分位排名位于 (0, 1]；密集排名在并列组之间不跳号。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        ascending : bool, default true
            true 时最小值排名最前；false 时最大值排名最前。
        ties_method : {"min", "max", "average", "first", "dense"}, default "min"
            并列值处理方式：
            * "min"：并列组使用该组的最小名次。
            * "max"：并列组使用该组的最大名次。
            * "average"：并列组使用所占名次的平均值。
            * "first"：按输入中的出现顺序为并列值分配不同名次。
            * "dense"：类似 "min"，但下一组名次只增加 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：排名忽略 NULL，原输入为 NULL 的位置返回 NULL；百分位分母只包含有效值。

        排名语义：返回 (0, 1] 内百分位；ascending 和 ties_method 控制排名。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        ties_method="min"：
        >>> cs_unary_rank_pct(col, true, "min")
        [0.2, 0.4, 0.4, 0.8, 1]

        ties_method="max"：
        >>> cs_unary_rank_pct(col, true, "max")
        [0.2, 0.6, 0.6, 0.8, 1]

        ties_method="average"：
        >>> cs_unary_rank_pct(col, true, "average")
        [0.2, 0.5, 0.5, 0.8, 1]

        ties_method="first"：
        >>> cs_unary_rank_pct(col, true, "first")
        [0.2, 0.4, 0.6, 0.8, 1]

        ties_method="dense"：
        >>> cs_unary_rank_pct(col, true, "dense")
        [0.25, 0.5, 0.5, 0.75, 1]

        降序排名：
        >>> cs_unary_rank_pct(col, false, "min")
        [1, 0.6, 0.6, 0.4, 0.2]
        */
        return cross_section_rank(col, ascending, ties_method, true)
    }
    """,
    dependencies=(CROSS_SECTION_RANK,)
)

CS_UNARY_ROBUST_ZSCORE = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_robust_zscore(col, scale) {
        /*
        使用中位数和 MAD 计算对异常值更稳健的 z-score。

        中心使用中位数，尺度使用scale * MAD。尺度为 0 或 NULL 时整个结果返回 NULL。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        scale : float, default 1.4826
            MAD 尺度系数。默认 1.4826 使正态分布下的 MAD 与标准差尺度近似一致。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：中位数和 MAD 忽略 NULL，原输入缺失位置仍返回 NULL；MAD 乘以 scale 后为 0
        时整个有效截面也返回 NULL。

        尺度语义：使用中位数中心化，并以 MAD * scale 作为尺度；scale 通常取 1.4826
        以兼容正态分布下的标准差估计。结果只在当前截面内标准化。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        scale=1.0：
        >>> cs_unary_robust_zscore(col, 1.0)
        [-1, 0, 0, 2, 6]

        scale=1.4826：
        >>> cs_unary_robust_zscore(col, 1.4826)
        [-0.674491, 0, 0, 1.34898, 4.04694]

        scale=2.0：
        >>> cs_unary_robust_zscore(col, 2.0)
        [-0.5, 0, 0, 1, 3]
        */
        center = med(col)
        deviation = mad(col, true) * scale
        if (isNull(deviation) || deviation == 0) return take(double(NULL), size(col))
        return (col - center) / deviation
    }
    """
)

CS_UNARY_SKEW = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_skew(col) {
        /*
        计算当前截面的偏度并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面统计忽略 NULL，并把单个统计量广播到截面全部位置，包括原输入为 NULL
        的位置；没有足够有效样本时广播 NULL。

        输出形状：结果与输入等长，每个位置保存相同统计量。输出为截面偏度的广播向量，而不是逐元素变换。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_skew(col)
        [1.00388, 1.00388, 1.00388, 1.00388, 1.00388]

        有效样本足够时，NULL 不阻断截面统计：
        >>> all(!isNull(cs_unary_skew(double([1, NULL, 2, 3, 4, 5]))))
        true
        */
        return broadcast_like(skew(col), col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_STD = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_std(col, ddof) {
        /*
        计算当前截面的标准差并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        ddof : {0, 1}, default 1
            自由度修正。0 使用总体统计量，分母为 N；1 使用样本统计量，分母为 N - 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面统计忽略 NULL，并把单个统计量广播到截面全部位置，包括原输入为 NULL
        的位置；没有足够有效样本时广播 NULL。 std/var 的有效样本数必须大于 ddof。

        输出形状：结果与输入等长，每个位置保存相同统计量。ddof 决定总体或样本估计口径；结果广播到整个截面。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        总体统计口径，ddof=0：
        >>> cs_unary_std(col, 0)
        [2.498, 2.498, 2.498, 2.498, 2.498]

        样本统计口径，ddof=1：
        >>> cs_unary_std(col, 1)
        [2.79285, 2.79285, 2.79285, 2.79285, 2.79285]
        */
        value = iif(int(ddof) == 0, stdp(col), std(col))
        return broadcast_like(value, col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_SUM = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_sum(col) {
        /*
        计算当前截面的总和并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面统计忽略 NULL，并把单个统计量广播到截面全部位置，包括原输入为 NULL
        的位置；没有足够有效样本时广播 NULL。

        输出形状：结果与输入等长，每个位置保存相同统计量。输出为截面总和的广播向量，而不是逐元素变换。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0
        >>> cs_unary_sum(col)
        [17, 17, 17, 17, 17]

        求和跳过 NULL 并广播：
        >>> cs_unary_sum(double([1, NULL, 3]))
        [4, 4, 4]
        */
        return broadcast_like(sum(col), col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_TOP_N = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_top_n(col, n) {
        /*
        标记当前截面中数值最大的 n 个有效观测。

        选择结果为布尔向量。并列值按原始出现顺序打破平局，使最终入选数量可确定。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        n : int
            需要标记的有效观测数量，必须至少为 1。

        Returns
        -------
        result : vector[BOOL]
            与 col 等长的 BOOL 选择标记。

        Notes
        -----
        NULL 处理：排名只使用非 NULL 观测，原输入为 NULL 的位置明确返回
        false，不会占用顶部或底部的选择名额。全 NULL 截面返回全 false。

        选择边界：按降序选择最多 n 个有效观测；n 超过有效样本数时全体有效值入选。并列值以 first
        规则按原顺序打破。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        选择 1 个观测：
        >>> cs_unary_top_n(col, 1)
        [false, false, false, false, true]

        选择 2 个观测：
        >>> cs_unary_top_n(col, 2)
        [false, false, false, true, true]

        选择 3 个观测：
        >>> cs_unary_top_n(col, 3)
        [false, true, false, true, true]
        */
        return !isNull(col) && (rank(col, false, , true, `first, false) < int(n))
    }
    """
)

CS_UNARY_TOP_PCT = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_top_pct(col, pct) {
        /*
        标记当前截面中位于顶部指定比例的有效观测。

        选择结果为布尔向量。并列值按原始出现顺序打破平局，使最终入选数量可确定。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        pct : float
            需要标记的有效观测比例，取值范围为 (0, 1]；数量向上取整。

        Returns
        -------
        result : vector[BOOL]
            与 col 等长的 BOOL 选择标记。

        Notes
        -----
        NULL 处理：排名只使用非 NULL 观测，原输入为 NULL 的位置明确返回
        false，不会占用顶部或底部的选择名额。全 NULL 截面返回全 false。

        选择边界：按降序选择 ceil(有效样本数 * pct) 个观测。并列值以 first 规则按原顺序打破。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        选择 20%：
        >>> cs_unary_top_pct(col, 0.2)
        [false, false, false, false, true]

        选择 40%：
        >>> cs_unary_top_pct(col, 0.4)
        [false, false, false, true, true]

        选择 60%：
        >>> cs_unary_top_pct(col, 0.6)
        [false, true, false, true, true]
        */
        return !isNull(col) && (rank(col, false, , true, `first, false) < ceil(count(col) * pct))
    }
    """
)

CS_UNARY_VAR = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_var(col, ddof) {
        /*
        计算当前截面的方差并广播结果。

        统计时忽略 NULL，并把单个截面统计值广播为与 col 等长的向量。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        ddof : {0, 1}, default 1
            自由度修正。0 使用总体统计量，分母为 N；1 使用样本统计量，分母为 N - 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：截面统计忽略 NULL，并把单个统计量广播到截面全部位置，包括原输入为 NULL
        的位置；没有足够有效样本时广播 NULL。 std/var 的有效样本数必须大于 ddof。

        输出形状：结果与输入等长，每个位置保存相同统计量。ddof 决定总体或样本估计口径；结果广播到整个截面。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        总体统计口径，ddof=0：
        >>> cs_unary_var(col, 0)
        [6.24, 6.24, 6.24, 6.24, 6.24]

        样本统计口径，ddof=1：
        >>> cs_unary_var(col, 1)
        [7.8, 7.8, 7.8, 7.8, 7.8]
        */
        // use ta 导入的 var 是移动方差；covar(col, col) 才是截面样本方差。
        value = iif(int(ddof) == 0, varp(col), covar(col, col))
        return broadcast_like(value, col)
    }
    """,
    dependencies=(BROADCAST_LIKE,)
)

CS_UNARY_WINSORIZE = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_winsorize(col, lower, upper) {
        /*
        把当前截面低于和高于指定分位数的值缩尾到对应边界。

        先计算 lower 和 upper 对应的截面分位数，再把超出范围的值替换为对应边界；范围内的值保持不变。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        lower : float, default 0.01
            用于计算缩尾边界的下侧分位数；必须满足 lower < upper。
        upper : float, default 0.99
            用于计算缩尾边界的上侧分位数；必须满足 lower < upper。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：计算分位数时忽略 NULL，原输入为 NULL 的位置保持
        NULL；截面没有有效尺度时无法产生有效截断边界。

        截断语义：仅把边界外数值替换为边界值，不删除行、不改变边界内排序，也不在截断后自动执行标准化。

        Examples
        --------
        >>> col = 1.0 2.0 3.0 4.0 100.0

        10%/90% 分位数缩尾：
        >>> cs_unary_winsorize(col, 0.1, 0.9)
        [1.4, 2, 3, 4, 61.6]

        20%/80% 分位数缩尾：
        >>> cs_unary_winsorize(col, 0.2, 0.8)
        [1.8, 2, 3, 4, 23.2]

        30%/70% 分位数缩尾：
        >>> cs_unary_winsorize(col, 0.3, 0.7)
        [2.2, 2.2, 3, 3.8, 3.8]
        */
        low_value = quantile(col, lower)
        high_value = quantile(col, upper)
        clipped = iif(col < low_value, low_value, iif(col > high_value, high_value, col))
        return iif(isNull(col), col, clipped)
    }
    """
)

CS_UNARY_WINSORIZE_MAD = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_winsorize_mad(col, n, scale) {
        /*
        使用中位数与 MAD 给出的上下界对当前截面缩尾。

        上下界为 median(col) ± n * scale * MAD(col)。超出边界的值被截断到边界，范围内的值保持不变。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        n : float, default 3.0
            MAD 边界倍数，必须大于 0。
        scale : float, default 1.4826
            MAD 尺度系数。默认 1.4826 使正态分布下的 MAD 与标准差尺度近似一致。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：计算中位数和 MAD 时忽略 NULL，原输入为 NULL 的位置保持
        NULL；截面没有有效尺度时无法产生有效截断边界。

        截断语义：仅把边界外数值替换为边界值，不删除行、不改变边界内排序，也不在截断后自动执行标准化。

        Examples
        --------
        >>> col = 1.0 2.0 3.0 4.0 100.0

        使用 1.0 倍 MAD 边界：
        >>> cs_unary_winsorize_mad(col, 1.0, 1.4826)
        [1.5174, 2, 3, 4, 4.4826]

        使用 2.0 倍 MAD 边界：
        >>> cs_unary_winsorize_mad(col, 2.0, 1.4826)
        [1, 2, 3, 4, 5.9652]

        使用 3.0 倍 MAD 边界：
        >>> cs_unary_winsorize_mad(col, 3.0, 1.4826)
        [1, 2, 3, 4, 7.4478]
        */
        center = med(col)
        distance = mad(col, true) * scale * n
        clipped = iif(col < center - distance, center - distance, iif(col > center + distance, center + distance, col))
        return iif(isNull(col), col, clipped)
    }
    """
)

CS_UNARY_ZSCORE = DolphinDBFunction(
    module="query",
    definition="""
    def cs_unary_zscore(col, ddof) {
        /*
        使用当前截面的均值和标准差计算 z-score。

        中心使用算术平均值，尺度使用标准差。尺度为 0 或 NULL 时整个结果返回 NULL。

        Parameters
        ----------
        col : vector
            当前截面的数值向量；NULL 不作为有效观测参加统计。
        ddof : {0, 1}, default 1
            自由度修正。0 使用总体统计量，分母为 N；1 使用样本统计量，分母为 N - 1。

        Returns
        -------
        result : vector[NUMBER]
            与输入等长的截面数值向量。

        Notes
        -----
        NULL 处理：均值和标准差忽略 NULL，原输入缺失位置仍返回 NULL；标准差为 0 或有效样本数不满足
        ddof 时整个有效截面也返回 NULL。

        尺度语义：使用均值中心化，由 ddof 选择总体或样本标准差。结果只在当前截面内标准化。

        Examples
        --------
        >>> col = 1.0 2.0 2.0 4.0 8.0

        总体统计口径，ddof=0：
        >>> cs_unary_zscore(col, 0)
        [-0.960769, -0.560449, -0.560449, 0.240192, 1.84147]

        样本统计口径，ddof=1：
        >>> cs_unary_zscore(col, 1)
        [-0.859338, -0.50128, -0.50128, 0.214834, 1.64706]
        */
        scale = iif(int(ddof) == 0, stdp(col), std(col))
        if (isNull(scale) || scale == 0) return take(double(NULL), size(col))
        return (col - avg(col)) / scale
    }
    """
)

CROSS_SECTION_OPERATOR_FUNCTIONS = (
    CS_BINARY_ALPHA,
    CS_BINARY_BETA,
    CS_BINARY_CORR,
    CS_BINARY_COV,
    CS_BINARY_RANK_CORR,
    CS_BINARY_RESIDUAL,
    CS_CONTROLS_ALPHA,
    CS_CONTROLS_BETA,
    CS_CONTROLS_RESIDUAL,
    CS_GROUPED_DEMEAN,
    CS_GROUPED_MEAN,
    CS_GROUPED_RANK_PCT,
    CS_GROUPED_ZSCORE,
    CS_UNARY_BOTTOM_N,
    CS_UNARY_BOTTOM_PCT,
    CS_UNARY_COUNT,
    CS_UNARY_DEMEAN,
    CS_UNARY_KURT,
    CS_UNARY_MAD,
    CS_UNARY_MAX,
    CS_UNARY_MEAN,
    CS_UNARY_MEDIAN,
    CS_UNARY_MIN,
    CS_UNARY_NORMALIZE_L1,
    CS_UNARY_NORMALIZE_L2,
    CS_UNARY_NORMALIZE_SUM,
    CS_UNARY_QCUT,
    CS_UNARY_QUANTILE,
    CS_UNARY_RANK,
    CS_UNARY_RANK_DENSE,
    CS_UNARY_RANK_NORMAL,
    CS_UNARY_RANK_PCT,
    CS_UNARY_ROBUST_ZSCORE,
    CS_UNARY_SKEW,
    CS_UNARY_STD,
    CS_UNARY_SUM,
    CS_UNARY_TOP_N,
    CS_UNARY_TOP_PCT,
    CS_UNARY_VAR,
    CS_UNARY_WINSORIZE,
    CS_UNARY_WINSORIZE_MAD,
    CS_UNARY_ZSCORE,
)
