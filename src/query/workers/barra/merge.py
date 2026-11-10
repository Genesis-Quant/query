"""Merge.dos的清洗与合成；可靠估计样本和需要覆盖的证券分开管理。"""

MERGE_SCRIPT = r"""
def winsorized(values) {
    // 官方MAD流程：median ± 3 * 1.4826 * median(abs(x-median))。
    finite = iif(isValid(values) && !isNanInf(double(values), true), double(values), double(NULL))
    center = median(finite)
    scale = median(abs(finite-center)) * 1.4826
    if (!isValid(scale)) return finite
    return clip(finite, center-3*scale, center+3*scale)
}

def standardized(values, capitalization) {
    // 沿用Merge的sqrt(total_market_value)加权中心、等权样本标准差。
    valid = isValid(values) && isValid(capitalization) && capitalization > 0
    output = take(double(NULL), size(values))
    if (!any(valid)) return output
    selected = double(values[valid])
    scale = std(selected)
    if (size(selected) < 2 || !isValid(scale)) return output
    if (scale == 0) output[valid] = take(0.0, size(selected))
    else output[valid] = (selected-wavg(selected, sqrt(capitalization[valid]))) / scale
    return output
}

def getRegTable(rawFactors, industryTable, descriptors, minimumCoverage=0.5, minimumStocks=2, allowWarmup=false, exposureLimit=5.0) {
    /* 非ST、上市历史和原料覆盖率约束只用于估计样本，不再直接删除可覆盖证券。
     * 缺失描述子只使用同日估计样本的行业均值、截面均值；不bfill，不伪造全缺因子。
     */
    if (rawFactors.rows() == 0) throw "Barra DSL没有返回数据"
    duplicated = select count(*) as copies from rawFactors group by time, code
    if (any(duplicated.copies > 1)) throw "Barra DSL存在重复日期证券键"
    duplicates = select count(*) as copies from industryTable group by time, code
    if (any(duplicates.copies > 1)) throw "Barra行业查询存在重复日期证券键"
    joined = lj(rawFactors, industryTable, `time`code)
    joined = select * from joined order by time, code
    available = take(0, joined.rows())
    for (factor in descriptors) {
        if (!(factor in joined.columnNames())) throw "DSL缺少Barra描述子：" + factor
        values = double(joined[factor])
        values = iif(isValid(values) && !isNanInf(values, true), values, double(NULL))
        joined[factor] = values
        available += int(isValid(values))
    }
    market = isValid(joined.market_cap) && joined.market_cap > 0 && !isNanInf(joined.market_cap,true) &&
        isValid(joined.float_cap) && joined.float_cap > 0 && !isNanInf(joined.float_cap,true)
    if ("market_valid" in joined.columnNames()) market = market && nullFill(joined.market_valid,false)
    industry = isValid(joined.industry) && joined.industry > 0
    included = nullFill(market && industry && available > 0,false)
    joined["observed_descriptors"] = available
    joined["estimation_eligible"] = included && nullFill(joined.eligible, false) && double(available)/size(descriptors) >= minimumCoverage
    joined["included"] = included
    reason = iif(!market,"invalid_market_or_capitalization",iif(!industry,"missing_industry",iif(available == 0,"no_descriptors","")))
    // 所有候选证券都有审计行；从未上市、退市后和无市值证券不会靠历史填充重新出现。
    stockCoverage = table(joined.time, string(joined.code) as code,
        long(available) as observed_descriptors,
        long(iif(included,size(descriptors)-available,0)) as imputed_descriptors,
        double(available)/size(descriptors) as raw_coverage,
        joined.estimation_eligible, included, string(reason) as exclusion_reason)
    for (name in ["market_cap_proxy","float_cap_proxy"]) {
        values = take(false,joined.rows())
        if (name in joined.columnNames()) values = nullFill(joined[name],false)
        stockCoverage[name] = values
    }
    if ("is_st" in joined.columnNames()) stockCoverage["is_st"] = nullFill(joined.is_st == 1,false)
    if ("history_observations" in joined.columnNames()) stockCoverage["listing_observations"] = long(joined.history_observations)
    selected = select * from joined where included == true
    if (selected.rows() == 0 && !allowWarmup) throw "Barra没有行情、行业及原始描述子有效的证券"
    processed = table(selected.time, string(selected.code) as code, selected.market_cap,
        selected.float_cap, selected.return_day, selected.benchmark_return,
        selected.return_valid, int(selected.industry) as industry, selected.estimation_eligible)
    addColumn(processed, symbol(descriptors), take(DOUBLE, size(descriptors)))
    audit = table(1:0, `time`factor`rows`observed`imputed`mad`scale`degenerate`clipped,
        [TIMESTAMP,STRING,LONG,LONG,LONG,DOUBLE,DOUBLE,BOOL,LONG])
    readiness = table(1:0, `time`stocks`estimation_stocks`missing`ready, [TIMESTAMP,LONG,LONG,STRING,BOOL])
    for (current in sort(distinct(rawFactors.time))) {
        indices = at(selected.time == current)
        donors = indices[selected.estimation_eligible[indices]]
        missing = array(STRING, 0)
        if (size(donors) < minimumStocks) missing.append!("estimation_stocks<" + string(minimumStocks))
        for (factor in descriptors) {
            if (count(selected[factor][donors]) < 2) missing.append!(factor)
        }
        readiness.append!(table([timestamp(current)] as time, [long(size(indices))] as stocks,
            [long(size(donors))] as estimation_stocks, [concat(missing, ",")] as missing,
            [size(missing) == 0] as ready))
    }
    ready = false
    for (current in sort(distinct(selected.time))) {
        indices = at(selected.time == current)
        if (!ready) {
            status = select * from readiness where time == current
            if (!status.ready[0]) continue
            ready = true
            selected = select * from selected where time >= current
            processed = select * from processed where time >= current
            indices = at(selected.time == current)
        }
        mask = selected.estimation_eligible[indices]
        industries = selected.industry[indices]
        caps = selected.market_cap[indices]
        for (factor in descriptors) {
            values = double(selected[factor][indices])
            donors = values[mask]
            if (count(donors) < 2) throw "Barra描述子估计样本不足：" + factor + " @ " + string(current)
            center = median(donors)
            spread = median(abs(donors-center))*1.4826
            if (!isValid(spread) || isNanInf(spread,true)) throw "Barra描述子MAD无效：" + factor
            // MAD为0表示估计样本的稳健截面退化，仍按同一边界裁剪，不能放大样本外新股。
            clipped = clip(values, center-3*spread, center+3*spread)
            donorClipped = clipped[mask]
            scale = std(donorClipped)
            if (!isValid(scale)) throw "Barra标准化有效样本不足：" + factor
            normalized = iif(isValid(values), 0.0, double(NULL))
            if (scale > 0) normalized = (clipped-wavg(donorClipped, sqrt(caps[mask])))/scale
            normalized = clip(normalized,-exposureLimit,exposureLimit)
            donorValues = iif(mask, normalized, double(NULL))
            industryMean = contextby(avg, donorValues, industries)
            filled = nullFill(normalized, industryMean)
            filled = nullFill(filled, avg(donorValues))
            if (any(isNull(filled))) throw "Barra同日估计样本无法填补：" + factor
            column = processed[factor]
            column[indices] = filled
            processed[factor] = column
            observed = count(values)
            audit.append!(table([timestamp(current)] as time, [factor] as factor,
                [long(size(values))] as rows, [long(observed)] as observed,
                [long(size(values)-observed)] as imputed, [spread] as mad,
                [scale] as scale, [spread == 0 || scale == 0] as degenerate,
                [long(sum(isValid(values) && (values < center-3*spread || values > center+3*spread)))] as clipped))
        }
    }
    if (!ready) {
        if (!allowWarmup) throw "Barra三级因子尚无完成预热的估计样本截面"
        processed = processed[0:0]
        stockCoverage["included"] = take(false, stockCoverage.rows())
        stockCoverage["imputed_descriptors"] = take(0l, stockCoverage.rows())
        stockCoverage["exclusion_reason"] = iif(stockCoverage.exclusion_reason == "",
            "cross_section_not_ready", stockCoverage.exclusion_reason)
    }
    return dict(`data`coverage`readiness`stock_coverage, [processed, audit, readiness, stockCoverage])
}

def getFSLevelFactor(factorsTable, firstFactors, secondFactors, exposureLimit=5.0) {
    /* 一级合成沿用等权关系；中心和尺度只由可靠估计样本决定。
     * 覆盖集合的ST、新股或高填补证券不会反过来改变可靠样本的标准化。
     */
    second = table(factorsTable.time, factorsTable.code)
    for (name in secondFactors.keys()) {
        components = string(secondFactors[name])
        values = take(0.0, factorsTable.rows())
        for (factor in components) values += double(factorsTable[factor])/size(components)
        second[name] = values
    }
    result = select time, code, market_cap, float_cap, return_day, benchmark_return,
        return_valid, industry from factorsTable
    estimation = take(true, result.rows())
    if ("estimation_eligible" in factorsTable.columnNames()) {
        estimation = factorsTable.estimation_eligible
        result["estimation_eligible"] = estimation
    }
    for (name in firstFactors.keys()) {
        values = take(0.0, second.rows())
        for (factor in string(firstFactors[name])) values += double(second[factor])/size(firstFactors[name])
        normalized = take(double(NULL), second.rows())
        for (current in sort(distinct(result.time))) {
            indices = at(result.time == current)
            mask = estimation[indices]
            donors = values[indices][mask]
            caps = result.market_cap[indices][mask]
            scale = std(donors)
            if (count(donors) < 2 || !isValid(scale)) throw "Barra一级因子估计样本不足：" + name
            if (scale == 0) normalized[indices] = take(0.0, size(indices))
            else normalized[indices] = clip((values[indices]-wavg(donors, sqrt(caps)))/scale,-exposureLimit,exposureLimit)
        }
        if (any(isNull(normalized)) || any(isNanInf(normalized,true))) throw "Barra一级因子标准化失败：" + name
        result[name] = normalized
    }
    return select * from result order by time, code
}
"""
