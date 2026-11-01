"""定义查询源处理和 DSL 执行使用的 DolphinDB 函数。"""

from query.database.compile import DolphinDBFunction
from query.database.compile.common.functions import (
    CONTROLS_REGRESSION,
    CONTROLS_REGRESSION_BATCH,
    FILL_REGRESSION_INPUTS,
    IS_DICTIONARY_FORM,
    IS_FINITE_NUMBER,
    IS_SCALAR_FORM,
    IS_TABLE_FORM,
    IS_VECTOR_FORM,
    NORMALIZE_REGRESSION_FILL,
    REQUIRE_TABLE_COLUMNS,
    ROLLING_CONTROLS_REGRESSION,
    ROLLING_MIN_PERIODS,
)

FILL_NULL_COLUMN = DolphinDBFunction(
    module="query",
    definition="""
    def fill_null_column(mutable source, name, value) {
        // 使用指定标量替换单列中的 NULL，表内其他列保持不变。
        require_table_columns(source, [string(name)], "fill_null_column")
        source[string(name)] = nullFill(source[string(name)], value)
        return source
    }
    """,
    dependencies=(REQUIRE_TABLE_COLUMNS,),
)

FILL_OBSERVED_GROUP_NULL_COLUMN = DolphinDBFunction(
    module="query",
    definition="""
    def fill_observed_group_null_column(mutable source, name, groups, value) {
        // 只填充至少包含一个有效值的组；整组缺失时保留 NULL。
        require_table_columns(
            source,
            [string(name)],
            "fill_observed_group_null_column"
        )
        if (!is_vector_form(groups) || size(groups) != source.rows()) {
            throw "fill_observed_group_null_column 的 groups 必须与 source 等长"
        }
        if (source.rows() == 0) return source

        values = source[string(name)]
        observed = contextby(any, !isNull(values), groups)
        source[string(name)] = iif(
            observed,
            nullFill(values, value),
            values
        )
        return source
    }
    """,
    dependencies=(IS_VECTOR_FORM, REQUIRE_TABLE_COLUMNS),
)

FORWARD_FILL_COLUMN = DolphinDBFunction(
    module="query",
    definition="""
    def forward_fill_column(mutable source, name, groups, order) {
        // 按 groups 分组并按 order 排序，对单列执行前向填充。
        require_table_columns(source, [string(name)], "forward_fill_column")
        if (!is_vector_form(groups) || size(groups) != source.rows()) {
            throw "forward_fill_column 的 groups 必须与 source 等长"
        }
        if (!is_vector_form(order) || size(order) != source.rows()) {
            throw "forward_fill_column 的 order 必须与 source 等长"
        }
        source[string(name)] = contextby(
            ffill,
            source[string(name)],
            groups,
            order
        )
        return source
    }
    """,
    dependencies=(IS_VECTOR_FORM, REQUIRE_TABLE_COLUMNS),
)

NORMALIZE_ON = DolphinDBFunction(
    module="query",
    definition="""
    def normalize_on(on, n) {
        // 校验 on 为 BOOL，将标量广播为 n 行向量，并把 NULL 统一视为 false。
        if (type(on) != BOOL) {
            throw "DSL 的 on 必须是 BOOL，实际类型为 " + typestr(on)
        }
        result = on
        if (is_scalar_form(result)) result = take(result, n)
        if (!is_vector_form(result) || size(result) != n) {
            throw "DSL 的 on 必须是长度为 " + string(n) + " 的 BOOL 向量，实际为 " + typestr(result)
        }
        return nullFill(result, false)
    }
    """,
    dependencies=(IS_SCALAR_FORM, IS_VECTOR_FORM),
)

RESTORE_MASKED_ROWS = DolphinDBFunction(
    module="query",
    definition="""
    def restore_masked_rows(selected_result, mask, n) {
        // 把筛选后的结果按 mask 回填到原始 n 行位置，未选中的行保持 NULL。
        result = array(type(selected_result), n, n, NULL)
        if (n == 0) return result
        if (sum(mask) == 0) return result
        indices = (0..(n - 1))[mask]
        result[indices] = selected_result
        return result
    }
    """
)

SAMPLE_OPERANDS = DolphinDBFunction(
    module="query",
    definition="""
    def sample_operands(operands) {
        // 从每个操作数取一个样本，供空筛选分支推断算符返回类型。
        result = array(ANY, 0)
        for (operand in operands) {
            if (size(operand) == 0) result.append!(array(type(operand), 1, 1, NULL))
            else result.append!(take(operand, 1))
        }
        return result
    }
    """
)

SELECT_OPERANDS = DolphinDBFunction(
    module="query",
    definition="""
    def select_operands(operands, mask) {
        // 使用同一个行掩码筛选全部操作数，并保持操作数顺序不变。
        result = array(ANY, 0)
        for (operand in operands) result.append!(operand[mask])
        return result
    }
    """
)

APPLY_TIME_SERIES = DolphinDBFunction(
    module="query",
    definition="""
    def apply_time_series(func, operands, on, code, time, empty_result) {
        // on=NULL 时对全部行计算；否则筛选 true 行并把结果恢复到原始位置。
        n = size(operands[0])
        if (n == 0) return empty_result
        if (type(on) == VOID) return contextby(func, operands, code, time)
        mask = normalize_on(on, n)
        if (sum(mask) == 0) {
            sample = unifiedCall(func, sample_operands(operands))
            return restore_masked_rows(sample, mask, n)
        }
        selected = contextby(func, select_operands(operands, mask), code[mask], time[mask])
        return restore_masked_rows(selected, mask, n)
    }
    """,
    dependencies=(
        NORMALIZE_ON,
        RESTORE_MASKED_ROWS,
        SAMPLE_OPERANDS,
        SELECT_OPERANDS,
    ),
)

APPLY_CROSS_SECTION = DolphinDBFunction(
    module="query",
    definition="""
    def apply_cross_section(func, operands, on, time, empty_result) {
        // on=NULL 时对全部行计算；否则筛选 true 行并把结果恢复到原始位置。
        n = size(operands[0])
        if (n == 0) return empty_result
        if (type(on) == VOID) return contextby(func, operands, time)
        mask = normalize_on(on, n)
        if (sum(mask) == 0) {
            sample = unifiedCall(func, sample_operands(operands))
            return restore_masked_rows(sample, mask, n)
        }
        selected = contextby(func, select_operands(operands, mask), time[mask])
        return restore_masked_rows(selected, mask, n)
    }
    """,
    dependencies=(
        NORMALIZE_ON,
        RESTORE_MASKED_ROWS,
        SAMPLE_OPERANDS,
        SELECT_OPERANDS,
    ),
)

APPLY_GROUPED_CROSS_SECTION = DolphinDBFunction(
    module="query",
    definition="""
    def apply_grouped_cross_section(func, operands, on, time, by, empty_result) {
        // on=NULL 时不按 on 筛选；by=NULL 始终不参与分组截面计算。
        n = size(operands[0])
        if (n == 0) return empty_result
        valid_group = !isNull(by)
        if (type(on) == VOID && sum(valid_group) == n) {
            return contextby(func, operands, (time, by))
        }
        mask = valid_group
        if (type(on) != VOID) mask = normalize_on(on, n) && valid_group
        if (sum(mask) == 0) {
            sample = unifiedCall(func, sample_operands(operands))
            return restore_masked_rows(sample, mask, n)
        }
        selected = contextby(func, select_operands(operands, mask), (time[mask], by[mask]))
        return restore_masked_rows(selected, mask, n)
    }
    """,
    dependencies=(
        NORMALIZE_ON,
        RESTORE_MASKED_ROWS,
        SAMPLE_OPERANDS,
        SELECT_OPERANDS,
    ),
)

APPLY_CONTROLLED_CROSS_SECTION = DolphinDBFunction(
    module="query",
    definition="""
    def apply_controlled_cross_section(func, target, controls, on, time) {
        // 按交易日向控制变量截面函数传入 target 和 controls，并把结果回填到原始行。
        n = size(target)
        result = array(DOUBLE, n, n, NULL)
        if (n == 0) return result
        selected_indices = 0..(n - 1)
        selected_time = time
        if (type(on) != VOID) {
            mask = normalize_on(on, n)
            if (sum(mask) == 0) return result
            selected_indices = selected_indices[mask]
            selected_time = selected_time[mask]
        }

        for (current_date in distinct(selected_time)) {
            row_indices = selected_indices[selected_time == current_date]
            result[row_indices] = func(target[row_indices], controls[row_indices])
        }
        return result
    }
    """,
    dependencies=(NORMALIZE_ON,),
)

APPLY_ROLLING_OLS = DolphinDBFunction(
    module="query",
    definition="""
    def apply_rolling_ols(target, controls, on, code, time, window, min_periods, intercept, fill="ffill") {
        /*
        按股票自己的 on 序列组织右对齐窗口；公共设计矩阵按日期分组后多目标拟合。
        行签名只用于候选筛选，合批前逐项核对完整窗口的时间、控制值和共同有效掩码。
        不同控制或缺失模式不共享系数；无可合批输入直接沿用逐股票路径。
        数值拟合由 common 辅助函数完成；结果恢复原行顺序，on=false/NULL 保持 NULL。
        fill 默认对目标和控制均 ffill；NULL 禁用，constant 和 mean 或逐列配置均先填
        当前 on 参与行再构造窗口。mean 仅用该日该列原始有限值，分类 mean 报错。
        不填输出、不向前补区间外历史；填补成功的输入计入 min_periods 和当天残差。
        */
        n = size(target)
        output = dict(STRING, ANY)
        output["alpha"] = take(double(NULL), n)
        output["residual"] = take(double(NULL), n)
        if (n == 0) return transpose(output)
        mask = take(true, n)
        if (type(on) != VOID) mask = normalize_on(on, n)
        selected = table(long(0 .. (n - 1)) as row_id, string(code) as code, timestamp(time) as time)
        selected = selected[mask]
        selected = select * from selected order by code, time, row_id
        input_target = target
        input_controls = controls
        fill_config = normalize_regression_fill(fill, controls.cols())
        if (any(fill_config.methods != "") && selected.rows() > 0) {
            indices = selected.row_id
            filled = fill_regression_inputs(target[indices], controls[indices], code[indices], time[indices], fill_config)
            input_target = take(double(NULL), n)
            input_target[indices] = filled.target
            input_controls = controls.copy()
            for (name in controls.columnNames()) {
                values = controls[name].copy()
                if (type(filled.controls[name]) == DOUBLE) values = double(values)
                values[indices] = filled.controls[name]
                replaceColumn!(input_controls, symbol([name])[0], values)
            }
        }
        if (window > 1 && selected.rows() >= int(window) * 2 && size(distinct(selected.code)) > 1) {
            minimum = rolling_min_periods(window, min_periods)
            if (isNull(window) || window < 1 || window != int(window) || minimum < 1 || minimum > window)
                throw "滚动回归窗口参数无效"
            if (!(type(input_target) in [CHAR, SHORT, INT, LONG, FLOAT, DOUBLE]))
                throw "回归 target 必须是数值"
            valid = is_finite_number(input_target)
            row_keys = array(ANY, 0)
            row_keys.append!(timestamp(time))
            for (name in input_controls.columnNames()) {
                values = input_controls[name]
                if (type(values) in [BOOL, SYMBOL, STRING]) valid = valid && isValid(values)
                else valid = valid && is_finite_number(values)
                row_keys.append!(values)
            }
            row_keys.append!(valid)
            signatures = contextby(min, long(0 .. (n - 1)), row_keys)
            selected["signature"] = signatures[selected.row_id]
            if (size(distinct(selected.signature)) * 2 <= selected.rows()) {
                selected["position"] = long(0 .. (selected.rows() - 1))
                selected["valid"] = valid[selected.row_id]
                selected["signature_hash"] = long(hashBucket(selected.signature, 2147483647))
                windows = select *,
                    mcount(signature, int(window), 1) as span,
                    msum(signature, int(window), 1) as key1,
                    msum(signature_hash, int(window), 1) as key2,
                    msum(int(valid), int(window), 1) as nobs
                    from selected context by code csort time, row_id
                candidates = select * from windows where nobs >= minimum
                batches = select toArray(position) as members from candidates
                    group by time, span, key1, key2, nobs having count(*) > 1
                handled = windows.nobs < minimum
                for (batch in 0 : batches.rows()) {
                    members = flatten(batches.members[batch,])
                    for (leader in members) {
                        if (handled[leader]) continue
                        first = leader - int(windows.span[leader]) + 1
                        positions = first .. leader
                        reference = windows.signature[positions]
                        peers = array(LONG, 0)
                        peer_windows = array(ANY, 0)
                        for (member in members[!handled[members]]) {
                            other = (member - int(windows.span[member]) + 1) .. member
                            if (all(reference == windows.signature[other])) {
                                peers.append!(member)
                                peer_windows.append!(windows.row_id[other])
                            }
                        }
                        if (size(peers) < 2) continue
                        valid_rows = windows.valid[positions]
                        targets = array(ANY, 0)
                        for (indices in peer_windows) targets.append!(double(input_target[indices[valid_rows]]))
                        indices = windows.row_id[positions]
                        fit = controls_regression_batch(
                            matrix(targets), input_controls[indices[valid_rows]], intercept, last(valid_rows)
                        )
                        rows = windows.row_id[peers]
                        output["alpha"][rows] = fit.alpha
                        output["residual"][rows] = fit.residual
                        if (size(fit.names) > 0) {
                            for (j in 0 .. (size(fit.names) - 1)) {
                                name = "beta" + string(j)
                                if (!(name in output)) output[name] = take(double(NULL), n)
                                output[name][rows] = flatten(fit.beta[j,])
                            }
                        }
                        handled[peers] = true
                    }
                }
                for (position in windows.position[!handled]) {
                    positions = (position - int(windows.span[position]) + 1) .. position
                    indices = windows.row_id[positions]
                    fit = controls_regression(input_target[indices], input_controls[indices], intercept)
                    row = windows.row_id[position]
                    output["alpha"][row] = fit.alpha
                    output["residual"][row] = last(fit.residual)
                    if (size(fit.beta) > 0) {
                        for (j in 0 .. (size(fit.beta) - 1)) {
                            name = "beta" + string(j)
                            if (!(name in output)) output[name] = take(double(NULL), n)
                            output[name][row] = fit.beta[j]
                        }
                    }
                }
                return transpose(output)
            }
        }
        for (current_code in distinct(selected.code)) {
            rows = select row_id, time from selected where code = current_code order by time, row_id
            indices = rows.row_id
            coefficients = rolling_controls_regression(
                input_target[indices], input_controls[indices], window, min_periods, intercept
            )
            for (name in coefficients.columnNames()) {
                if (!(name in output)) output[name] = take(double(NULL), n)
                values = output[name]
                values[indices] = coefficients[name]
                output[name] = values
            }
        }
        return transpose(output)
    }
    """,
    dependencies=(
        NORMALIZE_ON,
        ROLLING_CONTROLS_REGRESSION,
        CONTROLS_REGRESSION,
        CONTROLS_REGRESSION_BATCH,
        ROLLING_MIN_PERIODS,
        IS_FINITE_NUMBER,
        FILL_REGRESSION_INPUTS,
        NORMALIZE_REGRESSION_FILL,
    ),
)

BUILD_CONTROL_TABLE = DolphinDBFunction(
    module="query",
    definition="""
    def build_control_table(values) {
        // 将按顺序给出的控制变量向量组装成 control0、control1 等命名列的表。
        if (size(values) == 0) throw "控制变量至少包含一列"
        columns = dict(STRING, ANY)
        for (index in 0..(size(values) - 1)) {
            columns["control" + string(index)] = values[index]
        }
        result = transpose(columns)
        reorderColumns!(result, "control" + string(0 .. (size(values) - 1)))
        return result
    }
    """
)

REQUIRE_KEY = DolphinDBFunction(
    module="query",
    definition="""
    def require_key(object, key, location) {
        // 校验 object 为字典且包含必填 key，错误信息保留 DSL 所在位置。
        if (!is_dictionary_form(object)) {
            throw location + " 必须是字典，实际类型为 " + typestr(object)
        }
        if (!(key in object)) throw location + " 缺少必填键 " + key
        return object[key]
    }
    """,
    dependencies=(IS_DICTIONARY_FORM,),
)

REQUIRE_VECTOR = DolphinDBFunction(
    module="query",
    definition="""
    def require_vector(value, n, location) {
        // 将标量或单元素向量广播为 n 行，并拒绝其他长度或数据形态不符合要求的结果。
        result = value
        if (is_scalar_form(result)) result = take(result, n)
        if (is_vector_form(result) && size(result) == 1 && n != 1) result = take(result, n)
        if (!is_vector_form(result) || size(result) != n) {
            throw location + " 必须返回长度为 " + string(n) + " 的向量，实际为 " + typestr(result)
        }
        return result
    }
    """,
    dependencies=(IS_SCALAR_FORM, IS_VECTOR_FORM),
)

REQUIRE_COLUMN = DolphinDBFunction(
    module="query",
    definition="""
    def require_column(source, name, operation) {
        // 读取算符必需的输入列；缺列时报告具体算符和列名。
        if (!(name in columnNames(source))) {
            throw operation + " 要求输入表包含列 " + name
        }
        return source[name]
    }
    """
)

EMPTY_FACTOR_TIMELINE = DolphinDBFunction(
    module="query",
    definition="""
    def empty_factor_timeline(factors) {
        // 构造带 selected 标记和请求 factor 的零行查询时间线。
        result = table(
            array(TIMESTAMP, 0) as time,
            array(SYMBOL, 0) as code,
            array(BOOL, 0) as selected
        )
        if (size(factors) > 0) {
            addColumn(result, string(factors), take(DOUBLE, size(factors)))
        }
        return result
    }
    """
)

BUILD_DEFAULT_FACTOR_SOURCE = DolphinDBFunction(
    module="query",
    definition="""
    def build_default_factor_source(
            data,
            codes,
            factors,
            dates,
            start_time,
            end_time) {
        // 从统一长表完成筛选、交易日展开、事件时间线构造和长转宽。
        if (!is_table_form(data)) {
            throw "build_factor_source 的 data 必须是 table，实际为 " + typestr(data)
        }
        if (!is_vector_form(codes) || size(codes) == 0) {
            throw "build_factor_source 的 codes 必须是非空向量"
        }
        if (!is_vector_form(factors) || (size(factors) > 0 && type(factors) != STRING)) {
            throw "build_factor_source 的 factors 必须是 STRING 向量"
        }
        if (!is_vector_form(dates)) {
            throw "build_factor_source 的 dates 必须是时间向量"
        }
        if (size(dates) == 0) return empty_factor_timeline(factors)

        code_table = table(symbol(codes) as code)
        date_table = table(timestamp(dates) as time)
        universe = select time, code, true as selected from cj(date_table, code_table)
        if (size(factors) == 0) {
            return select * from universe order by code, time
        }

        values = select timestamp(time) as time, code, factor, value
            from data
            where time >= start_time
              and time < end_time
              and factor in symbol(factors)
              and code in symbol(codes)
        // 正式日期已有完整证券面板；只补入去重后的额外事件键，保留非交易日事件。
        events = select distinct time, code, false as selected from values
            where !(time in timestamp(dates))
        timeline = select max(selected) as selected
            from unionAll(universe, events)
            group by time, code

        if (values.rows() == 0) {
            wide = select time, code from values
        } else {
            wide = select first(value) from values pivot by time, code, factor
        }
        result = select * from lj(timeline, wide, ["time", "code"])
            order by code, time

        missing = string(factors)[!(string(factors) in columnNames(result))]
        if (size(missing) > 0) {
            addColumn(result, missing, take(DOUBLE, size(missing)))
        }
        reorderColumns!(
            result,
            ["time", "code", "selected"] join string(factors)
        )
        return result
    }
    """,
    dependencies=(
        EMPTY_FACTOR_TIMELINE,
        IS_TABLE_FORM,
        IS_VECTOR_FORM,
    ),
)

BUILD_FIXED_CODE_FACTOR_SOURCE = DolphinDBFunction(
    module="query",
    definition="""
    def build_fixed_code_factor_source(
            data,
            names,
            target_codes,
            target_factors,
            times,
            start_time,
            end_time) {
        // 在外部证券自己的时间线上按基础字段默认填充，再对齐原面板；不添加证券行。
        financial_factors = __FINANCIAL_FACTORS__
        industry_factors = __INDUSTRY_FACTORS__
        result = dict(STRING, ANY)
        for (target_code in distinct(target_codes)) {
            matched = target_codes == target_code
            base_factors = target_factors[matched]
            aliases = names[matched]
            reference_data = select
                    timestamp(date(time)) as time, code, factor, value
                from data
                where time >= start_time, time < end_time,
                      code = symbol([target_code])[0],
                      factor in symbol(base_factors)
            duplicates = select count(*) as copies from reference_data group by time, factor
            if (any(duplicates.copies > 1)) {
                throw "factor@code 每个日期只能有一条记录：" + target_code
            }
            timeline = sort(distinct(timestamp(times)))
            for (column in base_factors[startsWith(base_factors, "weight_")]) {
                observed = exec distinct timestamp(date(time)) from data
                    where factor = symbol([column])[0], time >= start_time, time < end_time
                timeline = sort(distinct(timeline join observed))
            }
            reference = build_default_factor_source(
                reference_data, [target_code], base_factors, timeline,
                start_time, end_time
            )
            for (i in 0 .. (size(base_factors) - 1)) {
                column = base_factors[i]
                if (column == "is_st") {
                    reference = fill_null_column(reference, column, 0.0)
                } else if (startsWith(column, "weight_")) {
                    observed = exec distinct timestamp(date(time)) from data
                        where factor = symbol([column])[0], time >= start_time, time < end_time
                    reference[column] = iif(
                        reference.time in observed,
                        nullFill(reference[column], 0.0), reference[column]
                    )
                    reference = forward_fill_column(
                        reference, column, reference.code, reference.time
                    )
                } else if (column in financial_factors || column in industry_factors) {
                    reference = forward_fill_column(
                        reference, column, reference.code, reference.time
                    )
                }
                mapping = dict(timestamp(reference.time), double(reference[column]))
                result[aliases[i]] = mapping[timestamp(times)]
            }
        }
        return result
    }
    """,
    dependencies=(BUILD_DEFAULT_FACTOR_SOURCE, FILL_NULL_COLUMN, FORWARD_FILL_COLUMN),
)

BUILD_FACTOR_SOURCE = DolphinDBFunction(
    module="query",
    definition="""
    def build_factor_source(
            data,
            codes,
            factors,
            dates,
            start_time,
            end_time) {
        if (!is_vector_form(factors) || (size(factors) > 0 && type(factors) != STRING)) {
            throw "build_factor_source 的 factors 必须是 STRING 向量"
        }
        if (size(distinct(factors)) != size(factors)) throw "factors 不能重复"
        defaults = array(STRING, 0)
        references = array(STRING, 0)
        reference_codes = array(STRING, 0)
        reference_factors = array(STRING, 0)
        for (name in string(factors)) {
            // 类型分发只在这里扩展；普通字段与固定证券引用各自独立构造。
            kind = iif(strReplace(name, "@", "") == name, "default", "fixed_code")
            if (kind == "default") {
                defaults.append!(name)
            } else if (kind == "fixed_code") {
                parts = split(name, "@")
                if (size(parts) != 2) throw "因子引用必须为 factor@code：" + name
                if (strlen(trim(parts[0])) == 0 || strlen(trim(parts[1])) == 0 ||
                    parts[0] != trim(parts[0]) || parts[1] != trim(parts[1])) {
                    throw "factor@code 的字段和代码不能为空或包含首尾空格：" + name
                }
                references.append!(name)
                reference_factors.append!(parts[0])
                reference_codes.append!(parts[1])
            } else {
                throw "不支持的因子引用类型：" + kind
            }
        }
        result = build_default_factor_source(
            data, codes, defaults, dates, start_time, end_time
        )
        if (result.rows() == 0) return empty_factor_timeline(factors)
        if (size(references) > 0) {
            fixed = build_fixed_code_factor_source(
                data, references, reference_codes, reference_factors,
                result.time, start_time, end_time
            )
            for (name in references) result[name] = fixed[name]
        }
        reorderColumns!(result, ["time", "code", "selected"] join string(factors))
        return result
    }
    """,
    dependencies=(
        BUILD_DEFAULT_FACTOR_SOURCE,
        BUILD_FIXED_CODE_FACTOR_SOURCE,
        EMPTY_FACTOR_TIMELINE,
        IS_VECTOR_FORM,
    ),
)

FINALIZE_FACTOR_SOURCE = DolphinDBFunction(
    module="query",
    definition="""
    def finalize_factor_source(source, factors) {
        // 填充完成后删除事件行和 selected 标记，返回正式日频 source。
        columns = ["time", "code", "selected"] join string(factors)
        require_table_columns(source, columns, "finalize_factor_source")
        selected = nullFill(source.selected, false)
        result = source[selected]
        dropColumns!(result, `selected)
        reorderColumns!(result, ["time", "code"] join string(factors))
        return result
    }
    """,
    dependencies=(REQUIRE_TABLE_COLUMNS,),
)

PROJECT_FACTOR_OUTPUT = DolphinDBFunction(
    module="query",
    definition="""
    def project_factor_output(source, names, start_time, end_time) {
        // 按输出日期区间筛选最终结果，并严格按照 names 返回列。
        columns = require_table_columns(source, names, "project_factor_output")
        if (!("time" in columns)) {
            throw "project_factor_output 的 names 必须包含 time"
        }
        selected = source.time >= start_time && source.time < end_time
        result = source[selected]
        extra = columnNames(result)[!(columnNames(result) in columns)]
        if (size(extra) > 0) dropColumns!(result, extra)
        reorderColumns!(result, columns)
        return result
    }
    """,
    dependencies=(REQUIRE_TABLE_COLUMNS,),
)

EVALUATE_DEFINITION = DolphinDBFunction(
    module="query",
    definition="""
    def evaluate_definition(evaluator, source, definitions, mutable cache, mutable states, name) {
        // 按名称递归计算因子，使用 cache 复用结果，并通过 states 检测循环依赖。
        if (name in cache) return cache[name]
        if (name in states && states[name] == 1) {
            throw "命名因子存在循环依赖，重复进入 " + name
        }
        if (!(name in definitions)) throw "不存在命名因子 " + name

        states[name] = 1
        value = evaluator(source, definitions, cache, states, definitions[name])
        value = require_vector(value, source.rows(), "命名因子 " + name)
        cache[name] = value
        states[name] = 2
        return value
    }
    """
)

EVALUATE_OPERAND = DolphinDBFunction(
    module="query",
    definition="""
    def evaluate_operand(evaluator, source, definitions, mutable cache, mutable states, operand) {
        // 将操作数解析为嵌套 DSL、命名因子、输入列或原样返回的标量。
        if (is_dictionary_form(operand)) {
            result = evaluator(source, definitions, cache, states, operand)
            if (is_vector_form(result) && size(result) == 1 && source.rows() != 1) {
                return take(result, source.rows())
            }
            return result
        }
        if (is_scalar_form(operand) && type(operand) == STRING) {
            if (operand in definitions) {
                return evaluate_definition(evaluator, source, definitions, cache, states, operand)
            }
            if (operand in columnNames(source)) return source[operand]
            throw "DSL 引用了不存在的列或命名因子 " + operand
        }
        if (is_scalar_form(operand)) return operand
        throw "DSL 操作数必须是列名、命名因子、嵌套节点或标量，实际为 " + typestr(operand)
    }
    """,
    dependencies=(IS_DICTIONARY_FORM, IS_SCALAR_FORM, IS_VECTOR_FORM),
)

EVALUATE_OPERANDS = DolphinDBFunction(
    module="query",
    definition="""
    def evaluate_operands(evaluator, source, definitions, mutable cache, mutable states, operands) {
        // 依次解析操作数列表，并以 ANY 数组保留不同结果类型。
        result = array(ANY, 0)
        for (operand in operands) {
            result.append!(evaluate_operand(evaluator, source, definitions, cache, states, operand))
        }
        return result
    }
    """
)

EVALUATE_FIELDS = DolphinDBFunction(
    module="query",
    definition="""
    def evaluate_fields(evaluator, source, definitions, mutable cache, mutable states, fields) {
        // 解析 DSL fields 字典；向量字段按操作数列表处理，其余字段按单个操作数处理。
        if (!is_dictionary_form(fields)) {
            throw "DSL fields 必须是字典，实际类型为 " + typestr(fields)
        }
        result = dict(STRING, ANY)
        for (name in string(fields.keys())) {
            operand = fields[name]
            if (is_vector_form(operand)) {
                result[name] = evaluate_operands(evaluator, source, definitions, cache, states, operand)
            } else {
                result[name] = evaluate_operand(evaluator, source, definitions, cache, states, operand)
            }
        }
        return result
    }
    """,
    dependencies=(IS_DICTIONARY_FORM, IS_VECTOR_FORM),
)

EVALUATE_NODE = DolphinDBFunction(
    module="query",
    definition="""
    def evaluate_node(source, definitions, mutable cache, mutable states, node) {
        // 校验 DSL 节点公共结构，并按 DIRECT、TS 或 CS 分发到对应执行器。
        node_type = require_key(node, "type", "DSL 节点")
        require_key(node, "op", "DSL 节点")
        require_key(node, "fields", "DSL 节点")
        require_key(node, "params", "DSL 节点")
        if (node_type == "DIRECT") {
            if ("on" in node) throw "DIRECT 节点禁止包含 on"
            return evaluate_direct(evaluate_node, source, definitions, cache, states, node)
        }
        if (node_type == "TS") {
            return evaluate_time_series(evaluate_node, source, definitions, cache, states, node)
        }
        if (node_type == "CS") {
            return evaluate_cross_section(evaluate_node, source, definitions, cache, states, node)
        }
        throw "未知 DSL 类型 " + string(node_type)
    }
    """
)

PARSE_DEFINITIONS = DolphinDBFunction(
    module="query",
    definition="""
    def parse_definitions(definitions) {
        // 接受标准 JSON 字符串或 ANY 字典，并规范化为命名因子定义集合。
        result = definitions
        if (is_scalar_form(result) && type(result) == STRING) result = fromStdJson(result)
        if (!is_dictionary_form(result)) {
            throw "派生因子集合必须是字典或标准 JSON 对象，实际为 " + typestr(result)
        }
        if (type(result) != ANY) {
            throw "派生因子字典的值类型必须为 ANY，实际为 " + typestr(result)
        }
        return result
    }
    """,
    dependencies=(IS_DICTIONARY_FORM, IS_SCALAR_FORM),
)

COMPUTE_FACTORS = DolphinDBFunction(
    module="query",
    definition="""
    def compute_factors(source, definitions) {
        // 计算全部命名因子并追加到 source 副本，同时拒绝因子名与输入列冲突。
        if (!is_table_form(source)) {
            throw "compute_factors 的 source 必须是 table，实际为 " + typestr(source)
        }
        parsed = parse_definitions(definitions)
        names = string(parsed.keys())
        conflicts = names[names in columnNames(source)]
        if (size(conflicts) > 0) {
            throw "命名因子与输入列重名：" + concat(conflicts, ", ")
        }

        cache = dict(STRING, ANY)
        states = dict(STRING, INT)
        result = select * from source
        for (name in names) {
            result[name] = evaluate_definition(evaluate_node, source, parsed, cache, states, name)
        }
        return result
    }
    """,
    dependencies=(IS_TABLE_FORM,),
)

FILTER_FACTORS = DolphinDBFunction(
    module="query",
    definition="""
    def filter_factors(source, filters) {
        // 仅保留全部 filters 列都为 true 的行；NULL 视为 false。
        if (!is_table_form(source)) {
            throw "filter_factors 的 source 必须是 table，实际为 " + typestr(source)
        }
        if (!is_vector_form(filters)) {
            throw "filter_factors 的 filters 必须是 STRING 向量，实际为 " + typestr(filters)
        }
        if (size(filters) == 0) return source
        if (type(filters) != STRING) {
            throw "filter_factors 的 filters 必须是 STRING 向量，实际为 " + typestr(filters)
        }

        names = string(filters)
        missing = names[!(names in columnNames(source))]
        if (size(missing) > 0) {
            throw "filters 对应列不存在：" + concat(missing, ", ")
        }

        mask = take(true, source.rows())
        for (name in names) {
            values = source[name]
            if (type(values) != BOOL) {
                throw "filters 对应列必须为 BOOL 类型：" + name + "=" + typestr(values)
            }
            mask = mask && nullFill(values, false)
        }
        return source[mask]
    }
    """,
    dependencies=(IS_TABLE_FORM, IS_VECTOR_FORM),
)

TOOL_FUNCTIONS = (
    NORMALIZE_ON,
    RESTORE_MASKED_ROWS,
    SAMPLE_OPERANDS,
    SELECT_OPERANDS,
    APPLY_TIME_SERIES,
    APPLY_CROSS_SECTION,
    APPLY_GROUPED_CROSS_SECTION,
    APPLY_CONTROLLED_CROSS_SECTION,
    APPLY_ROLLING_OLS,
    BUILD_CONTROL_TABLE,
    REQUIRE_KEY,
    REQUIRE_VECTOR,
    REQUIRE_COLUMN,
    FILL_OBSERVED_GROUP_NULL_COLUMN,
    FILL_NULL_COLUMN,
    FORWARD_FILL_COLUMN,
    BUILD_FACTOR_SOURCE,
    FINALIZE_FACTOR_SOURCE,
    PROJECT_FACTOR_OUTPUT,
)

DERIVE_HELPER_FUNCTIONS = (
    EVALUATE_DEFINITION,
    EVALUATE_OPERAND,
    EVALUATE_OPERANDS,
    EVALUATE_FIELDS,
)

DERIVE_ENTRY_FUNCTIONS = (
    EVALUATE_NODE,
    PARSE_DEFINITIONS,
    COMPUTE_FACTORS,
    FILTER_FACTORS,
)
