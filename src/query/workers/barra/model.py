"""Model.dos 的日频收益回归和风险估计；输入仅使用已取得的 DSL 数据。"""

MODEL_SCRIPT = r"""
def getAllFactorValidate(exposures, realized, styles, industries, minimumStocks) {
    /* t-1暴露解释t收益；使用t-1流通市值作为WLS目标权重。
     * 国家因子+行业哑变量使用市值加权行业收益和为0的约束，不以任意行业充当国家收益。
     */
    observations = select string(code) as code, double(return_day) as realized_return
        from realized where return_valid == true, isValid(return_day)
    covered = ej(exposures, observations, `code)
    covered = select * from covered where float_cap > 0, market_cap > 0 order by code
    sample = covered
    if ("estimation_eligible" in sample.columnNames())
        sample = select * from sample where estimation_eligible == true
    if (sample.rows() < minimumStocks) throw "Barra截面有效估计证券不足"
    levels = sort(distinct(int(sample.industry)))
    coveredIndustries = sort(distinct(int(exposures.industry)))
    if (any(!(coveredIndustries in levels))) throw "Barra覆盖行业没有有效估计样本，不能把未估计行业收益记为零"
    capital = array(DOUBLE, 0)
    for (level in levels) capital.append!(sum(sample.market_cap[sample.industry == level]))
    baseIndex = imax(capital)
    baseIndustry = levels[baseIndex]
    baseCapital = capital[baseIndex]
    names = ["country"] join string(styles) join ("industry_" + string(industries))
    design = array(ANY, 0)
    design.append!(take(1.0, sample.rows()))
    for (style in styles) design.append!(double(sample[style]))
    reduced = levels[levels != baseIndustry]
    for (level in reduced) {
        ratio = capital[find(levels, level)] / baseCapital
        design.append!(double(sample.industry == level) - ratio * double(sample.industry == baseIndustry))
    }
    weights = double(sample.float_cap) / sum(sample.float_cap)
    weighted = array(ANY, 0)
    for (column in design) weighted.append!(column * sqrt(weights))
    x = matrix(weighted)
    singular = svd(x, false, false)
    rankTolerance = max(singular) * max(x.rows(), x.cols()) * 2.220446049250313e-16
    effectiveRank = sum(singular > rankTolerance)
    if (effectiveRank < x.cols()) throw "Barra约束后设计矩阵不满列秩，拒绝不可辨识回归"
    if (sample.rows() <= effectiveRank) throw "Barra截面回归没有残差自由度"
    coefficients = (pinv(x) ** matrix(sample.realized_return * sqrt(weights)))[0]
    fitted = take(0.0, sample.rows())
    for (index in 0 : size(design)) fitted += design[index] * coefficients[index]
    residual = sample.realized_return - fitted
    values = take(0.0, size(names))
    values[0:(size(styles)+1)] = coefficients[0:(size(styles)+1)]
    baseReturn = 0.0
    for (index in 0 : size(reduced)) {
        level = reduced[index]
        coefficient = coefficients[size(styles)+1+index]
        values[find(names, "industry_"+string(level))] = coefficient
        baseReturn -= coefficient * capital[find(levels, level)] / baseCapital
    }
    values[find(names, "industry_"+string(baseIndustry))] = baseReturn
    if (any(!isValid(values)) || any(isNanInf(values, true))) throw "Barra回归返回非有限系数"
    total = wsum(pow(sample.realized_return-wavg(sample.realized_return, weights),2), weights)
    r2 = double(NULL)
    if (total > 0) r2 = 1.0-wsum(pow(residual,2),weights)/total
    // 系数只由估计样本决定，但为所有当日有真实收益的覆盖证券保留残差。
    coveredFit = take(values[0], covered.rows())
    for (index in 0 : size(styles)) coveredFit += double(covered[styles[index]])*values[index+1]
    for (level in industries) {
        coveredFit += double(covered.industry == level)*values[find(names, "industry_"+string(level))]
    }
    return dict(`factors`residuals`stocks`rank`r2, [
        table(names as factor, values as value),
        table(string(covered.code) as code, double(covered.realized_return-coveredFit) as value),
        long(sample.rows()), long(effectiveRank), r2])
}

def getRetTable(factorsTable, rawFactors, calendar, styles, industries, minimumStocks) {
    // 整段独立回归；原始交易日历的相邻日必须都有截面，不跨缺日配对。
    exposures = select * from factorsTable order by time, code
    realized = select time, code, return_day, return_valid from rawFactors order by time, code
    exposureCounts = select count(*) as rows from exposures group by time order by time
    realizedCounts = select count(*) as rows from realized group by time order by time
    if (any(!(timestamp(calendar) in timestamp(exposureCounts.time))) || any(!(timestamp(calendar) in timestamp(realizedCounts.time))))
        throw "Barra整段回归缺少交易日截面"
    exposureEnds = cumsum(exposureCounts.rows)
    exposureBegins = exposureEnds-exposureCounts.rows
    realizedEnds = cumsum(realizedCounts.rows)
    realizedBegins = realizedEnds-realizedCounts.rows
    returns = table(1:0, `time`factor`value, [TIMESTAMP,STRING,DOUBLE])
    residuals = table(1:0, `time`code`value, [TIMESTAMP,STRING,DOUBLE])
    diagnostics = table(1:0, `time`stocks`rank`r2, [TIMESTAMP,LONG,LONG,DOUBLE])
    for (index in 1 : size(calendar)) {
        current = calendar[index]
        previousPosition = find(timestamp(exposureCounts.time), timestamp(calendar[index-1]))
        currentPosition = find(timestamp(realizedCounts.time), timestamp(current))
        previous = exposures[exposureBegins[previousPosition]:exposureEnds[previousPosition]]
        today = realized[realizedBegins[currentPosition]:realizedEnds[currentPosition]]
        fit = getAllFactorValidate(previous, today, styles, industries, minimumStocks)
        returns.append!(table(take(current, fit.factors.rows()) as time, fit.factors.factor, fit.factors.value))
        residuals.append!(table(take(current, fit.residuals.rows()) as time, fit.residuals.code, fit.residuals.value))
        diagnostics.append!(table([current] as time, [fit.stocks] as stocks, [fit.rank] as rank, [fit.r2] as r2))
    }
    return dict(`factor_returns`specific_returns`diagnostics, [returns, residuals, diagnostics])
}

def Newye_West(ret, halfLife, q=5) {
    /* 指数衰减样本协方差 + Bartlett加权的双向滞后协方差。
     * 输出为日收益方差，不把日频矩阵默默乘252或当成月频风险。
     */
    observations = ret.rows()
    if (observations < 2 || halfLife <= 0) throw "风险估计需要至少两个观测和正半衰期"
    weights = pow(0.5, double((observations-1)-(0..(observations-1))) / halfLife)
    weights /= sum(weights)
    denominator = 1.0 - sum(weights*weights)
    centered = ret.copy()
    for (column in 0 : ret.cols()) centered[column] = ret[column] - wavg(ret[column], weights)
    weighted = centered.copy()
    for (column in 0 : ret.cols()) weighted[column] = centered[column] * sqrt(weights)
    covariance = (transpose(weighted) ** weighted) / denominator
    lags = min(int(q), observations-1)
    if (lags > 0) {
        for (lag in 1 .. lags) {
            recent = weighted[lag:observations,]
            earlier = weighted[0:(observations-lag),]
            gamma = (transpose(recent) ** earlier) / denominator
            covariance += (1.0-double(lag)/(lags+1)) * (gamma+transpose(gamma))
        }
    }
    return (covariance + transpose(covariance)) / 2.0
}

def specificVariance(values, halfLife, q, minimumObservations) {
    /* 缺失残差不压缩时间轴：只让其估计权重为0，绝不伪造一个有效的零收益。 */
    valid = isValid(values) && !isNanInf(double(values), true)
    if (sum(valid) < minimumObservations) return double(NULL)
    observations = size(values)
    weights = pow(0.5, double((observations-1)-(0..(observations-1))) / halfLife)
    weights = iif(valid, weights, 0.0)
    weights /= sum(weights)
    center = wavg(values[valid], weights[valid])
    weighted = iif(valid, double(values)-center, 0.0) * sqrt(weights)
    denominator = 1.0-sum(weights*weights)
    variance = sum(weighted*weighted) / denominator
    lags = min(int(q), observations-1)
    if (lags > 0) {
        for (lag in 1 .. lags) {
            covariance = sum(weighted[lag:observations]*weighted[0:(observations-lag)]) / denominator
            variance += 2.0*(1.0-double(lag)/(lags+1))*covariance
        }
    }
    return variance
}

def BayesShrinkage(specific, weight, q=1.0) {
    // 原教程按市值十分组收缩波动率；返回平方后的方差，不把波动率写入方差表。
    joined = ej(specific, weight, `code)
    joined = select * from joined order by market_cap, code
    joined["group"] = int(floor(double(0..(joined.rows()-1))*10/joined.rows()))
    joined["sigma"] = sqrt(joined.value)
    joined["prior"] = contextby(wavg, (joined.sigma, joined.market_cap), joined.group)
    deviation = pow(joined.sigma-joined.prior, 2)
    spread = sqrt(contextby(avg, deviation, joined.group))
    difference = abs(joined.sigma-joined.prior)
    denominator = spread + q*difference
    shrinkage = iif(denominator > 0, q*difference/denominator, 0.0)
    joined[`value] = pow(joined.sigma*(1.0-shrinkage)+joined.prior*shrinkage, 2)
    return select code, value from joined
}

def completeSpecificRisk(estimates, today, request) {
    /* 短历史证券用同日、同业及邻近市值的可靠方差作先验；不填残差、不读取未来。
     * 至少需要一组真实足量残差估计，不能在整个截面无风险原料时编造方差。
     */
    peers = select * from estimates where source == "history", value > 0,
        isValid(value), !isNanInf(value, true)
    if (peers.rows() == 0) throw "Barra没有足量历史特异风险可用于同日估计"
    if (!("specificPeerFallback" in request) || !request.specificPeerFallback)
        return select code, value, observations, source from peers
    output = select code, value, observations, source from peers
    targets = select * from today where !(code in output.code)
    if (targets.rows() == 0) return output
    peers = ej(peers, select code, market_cap, industry from today, `code)
    minimum = request.specificPeerMinStocks
    if ("estimation_eligible" in today.columnNames()) {
        trusted = exec code from today where estimation_eligible == true
        chosen = select * from peers where code in trusted
        if (chosen.rows() >= minimum) peers = chosen
    }
    if (peers.rows() < minimum) throw "Barra同日特异风险先验样本不足"
    for (index in 0 : targets.rows()) {
        stock = targets.code[index]
        level = targets.industry[index]
        capitalization = targets.market_cap[index]
        candidates = select * from peers where industry == level
        method = "industry_size_peer"
        if (candidates.rows() < minimum) {
            candidates = peers
            method = "market_size_peer"
        }
        distances = abs(log(candidates.market_cap/capitalization))
        order = isort(distances)
        countPeers = max(minimum, int(ceil(double(candidates.rows())/10)))
        candidates = candidates[order[0:min(countPeers,size(order))]]
        prior = median(candidates.value)
        observed = select * from estimates where code == stock
        observations = long(0)
        value = prior
        if (observed.rows() > 0) {
            observations = observed.observations[0]
            if (observations >= request.specificShortObservations && isValid(observed.value[0]) && observed.value[0] > 0) {
                weight = min(1.0, double(observations)/request.minimumSpecificObservations)
                value = weight*observed.value[0] + (1.0-weight)*prior
                method = "short_history_" + method
            }
        }
        if (!isValid(value) || isNanInf(value, true) || value <= 0)
            throw "Barra同日特异风险先验无效：" + stock
        output.append!(table([string(stock)] as code, [max(value,request.varianceFloor)] as value,
            [observations] as observations, [method] as source))
    }
    return output
}

def getRiskTablesFromReturns(factorsTable, fitted, calendar, styles, request) {
    /* t日输出使用t日暴露和截至t日的已实现因子收益，不访问t+1数据。
     * 个股短历史使用显式同日先验；截面收益或可靠先验全缺时仍报错。
     */
    // 固定行业字典不从未来截面推导，保证同一天在不同结束日期下具有相同因子轴。
    industries = int(request.industries)
    if (any(!(int(factorsTable.industry) in industries))) throw "Barra出现未声明的行业编码"
    names = ["country"] join string(styles) join ("industry_"+string(industries))
    if (fitted.factor_returns.rows() == 0) throw "Barra没有可用于风险估计的回归收益"
    factorWide = select first(value) from fitted.factor_returns pivot by time, factor
    reorderColumns!(factorWide, ["time"] join names)
    exposures = table(1:0, `time`code`factor`value, [TIMESTAMP,STRING,STRING,DOUBLE])
    covariance = table(1:0, `time`factor1`factor2`value, [TIMESTAMP,STRING,STRING,DOUBLE])
    specific = table(1:0, `time`code`value, [TIMESTAMP,STRING,DOUBLE])
    coverage = table(1:0, `time`factor_observations`eligible_stocks`risk_stocks`excluded_stocks`history_stocks`estimated_stocks,
        [TIMESTAMP,LONG,LONG,LONG,LONG,LONG,LONG])
    specificAudit = table(1:0, `time`code`observations`source, [TIMESTAMP,STRING,LONG,STRING])
    minimumHistory = max(request.minimumObservations, request.minimumSpecificObservations)
    dates = calendar[calendar >= request.start && calendar <= request.end]
    if (size(dates) == 0) throw "Barra分段没有目标交易日"
    if (size(calendar) <= minimumHistory || size(calendar[calendar <= dates[0]]) <= minimumHistory)
        throw "Barra分段首个目标日的风险预热历史不足，拒绝跳过目标日"
    ordered = select * from factorsTable order by time, code
    dailyCounts = select count(*) as rows from ordered group by time order by time
    dailyEnds = cumsum(dailyCounts.rows)
    dailyBegins = dailyEnds-dailyCounts.rows
    for (current in dates) {
        factorHistory = select * from factorWide where time <= current order by time
        if (factorHistory.rows() > request.covarianceWindow)
            factorHistory = factorHistory[(factorHistory.rows()-request.covarianceWindow):factorHistory.rows()]
        if (factorHistory.rows() < request.minimumObservations)
            throw "Barra因子风险历史不足："+string(current)
        matrixValues = matrix(factorHistory[symbol(names)])
        if (any(isNull(matrixValues))) throw "Barra因子收益日期或列不完整"
        cov = Newye_West(matrixValues, request.covarianceHalfLife, request.lags)
        eigen = eig(cov)
        if (min(eigen.values) < -1e-10) throw "Barra协方差不是半正定矩阵"
        // 只消除浮点舍入产生的负特征值，不用特征值下限伪造缺失风险。
        if (min(eigen.values) < 0) cov = eigen.vectors ** diag(iif(eigen.values < 0,0.0,eigen.values)) ** transpose(eigen.vectors)
        position = find(timestamp(dailyCounts.time), timestamp(current))
        if (position < 0 || position >= dailyCounts.rows()) throw "Barra目标日没有有效暴露"
        today = ordered[dailyBegins[position]:dailyEnds[position]]
        residualDays = calendar[calendar <= current]
        if (size(residualDays) > request.specificWindow)
            residualDays = residualDays[(size(residualDays)-request.specificWindow):size(residualDays)]
        residualWindow = select code, time, value from fitted.specific_returns
            where time in residualDays order by code, time
        counts = select count(*) as rows from residualWindow group by code order by code
        ends = cumsum(counts.rows)
        begins = ends - counts.rows
        positions = dict(STRING, INT)
        if (counts.rows() > 0) positions = dict(string(counts.code), int(0..(counts.rows()-1)))
        estimates = table(1:0, `code`value`observations`source, [STRING,DOUBLE,LONG,STRING])
        for (stock in today.code) {
            aligned = take(double(NULL), size(residualDays))
            if (string(stock) in positions.keys()) {
                position = positions[string(stock)]
                observations = residualWindow[begins[position]:ends[position]]
                aligned[find(timestamp(residualDays), timestamp(observations.time))] = observations.value
            }
            observed = long(sum(isValid(aligned) && !isNanInf(double(aligned), true)))
            variance = specificVariance(aligned, request.specificHalfLife, request.lags, 2)
            method = "short_history"
            if (observed >= request.minimumSpecificObservations) method = "history"
            if (isValid(variance) && !isNanInf(variance, true)) variance = max(variance, request.varianceFloor)
            estimates.append!(table([string(stock)] as code, [double(variance)] as value,
                [observed] as observations, [method] as source))
        }
        completed = completeSpecificRisk(estimates, today, request)
        risk = select code, value from completed
        if (request.shrink) risk = BayesShrinkage(risk, select code,market_cap from today)
        specificAudit.append!(table(take(current,completed.rows()) as time, completed.code,
            completed.observations, completed.source))
        validCodes = risk.code
        selected = select * from today where code in validCodes order by code
        for (factor in names) {
            values = take(1.0, selected.rows())
            if (factor in styles) values = double(selected[factor])
            else if (startsWith(factor, "industry_")) values = double(selected.industry == int(substr(factor,9)))
            exposures.append!(table(take(current,selected.rows()) as time, string(selected.code) as code,
                take(factor,selected.rows()) as factor, values as value))
        }
        for (index in 0 : size(names)) {
            covariance.append!(table(take(current,size(names)) as time,
                take(names[index],size(names)) as factor1, names as factor2,
                flatten(cov[index,]) as value))
        }
        specific.append!(table(take(current,risk.rows()) as time, risk.code, risk.value))
        historyCount = long(sum(completed.source == "history"))
        coverage.append!(table([current] as time, [long(factorHistory.rows())] as factor_observations,
            [long(today.rows())] as eligible_stocks, [long(risk.rows())] as risk_stocks,
            [long(today.rows()-risk.rows())] as excluded_stocks,
            [historyCount] as history_stocks, [long(risk.rows())-historyCount] as estimated_stocks))
    }
    return dict(`exposures`covariance`specific`factor_returns`specific_returns`regression`risk_coverage`specific_audit,
        [exposures,covariance,specific,fitted.factor_returns,fitted.specific_returns,fitted.diagnostics,coverage,specificAudit])
}

def getRiskTables(factorsTable, rawFactors, calendar, styles, request) {
    // 只允许本段开头尚未就绪的历史；本段目标日和就绪后的中间日期一律不能跳过。
    if (factorsTable.rows() == 0) throw "Barra整段没有有效风格截面"
    firstReady = min(factorsTable.time)
    target = calendar[calendar >= request.start && calendar <= request.end]
    if (size(target) == 0) throw "Barra整段没有有效目标日"
    if (firstReady > target[0]) throw "Barra分段首个目标日截面尚未就绪，拒绝跳过目标日"
    clock = calendar[calendar >= firstReady]
    fitted = getRetTable(factorsTable, rawFactors, clock, styles,
        int(request.industries), request.minimumStocks)
    return getRiskTablesFromReturns(factorsTable, fitted, clock, styles, request)
}
"""
