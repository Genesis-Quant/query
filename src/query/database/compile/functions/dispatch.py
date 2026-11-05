"""Static DolphinDB evaluator functions for query operators."""

from .function import DolphinDBFunction
from .numeric import (
    CALENDAR_ROLLING_PAIR,
    CALENDAR_ROLLING_UNARY,
    WEIGHTED_ROLLING_MEAN,
)

MODULE = "query"

EVALUATE_DIRECT = DolphinDBFunction(
    module=MODULE,
    definition=r"""
    def evaluate_direct(evaluator, source, definitions, mutable cache, mutable states, node) {
        // 解析 DIRECT 节点的 fields 和 params，并调用匹配的逐行算符函数。
        op = node["op"]
        fields = evaluate_fields(evaluator, source, definitions, cache, states, node["fields"])
        params = node["params"]

        if (op == "binary.add") {
            return direct_binary_add(fields["left"], fields["right"])
        }
        if (op == "binary.and") {
            return direct_binary_and(fields["left"], fields["right"])
        }
        if (op == "binary.days_between") {
            return direct_binary_days_between(fields["left"], fields["right"])
        }
        if (op == "binary.div") {
            return direct_binary_div(fields["left"], fields["right"])
        }
        if (op == "binary.eq") {
            return direct_binary_eq(fields["left"], fields["right"])
        }
        if (op == "binary.floor_div") {
            return direct_binary_floor_div(fields["left"], fields["right"])
        }
        if (op == "binary.ge") {
            return direct_binary_ge(fields["left"], fields["right"])
        }
        if (op == "binary.gt") {
            return direct_binary_gt(fields["left"], fields["right"])
        }
        if (op == "binary.le") {
            return direct_binary_le(fields["left"], fields["right"])
        }
        if (op == "binary.lt") {
            return direct_binary_lt(fields["left"], fields["right"])
        }
        if (op == "binary.maximum") {
            return direct_binary_maximum(fields["left"], fields["right"])
        }
        if (op == "binary.minimum") {
            return direct_binary_minimum(fields["left"], fields["right"])
        }
        if (op == "binary.mod") {
            return direct_binary_mod(fields["left"], fields["right"])
        }
        if (op == "binary.mul") {
            return direct_binary_mul(fields["left"], fields["right"])
        }
        if (op == "binary.ne") {
            return direct_binary_ne(fields["left"], fields["right"])
        }
        if (op == "binary.null_if") {
            return direct_binary_null_if(fields["left"], fields["right"])
        }
        if (op == "binary.or") {
            return direct_binary_or(fields["left"], fields["right"])
        }
        if (op == "binary.pow") {
            return direct_binary_pow(fields["left"], fields["right"])
        }
        if (op == "binary.sub") {
            return direct_binary_sub(fields["left"], fields["right"])
        }
        if (op == "binary.xor") {
            return direct_binary_xor(fields["left"], fields["right"])
        }
        if (op == "multiary.add") {
            return direct_multiary_add(fields["cols"])
        }
        if (op == "multiary.and") {
            return direct_multiary_and(fields["cols"])
        }
        if (op == "multiary.coalesce") {
            return direct_multiary_coalesce(fields["cols"])
        }
        if (op == "multiary.count") {
            return direct_multiary_count(fields["cols"])
        }
        if (op == "multiary.max") {
            return direct_multiary_max(fields["cols"])
        }
        if (op == "multiary.mean") {
            return direct_multiary_mean(fields["cols"])
        }
        if (op == "multiary.min") {
            return direct_multiary_min(fields["cols"])
        }
        if (op == "multiary.mul") {
            return direct_multiary_mul(fields["cols"])
        }
        if (op == "multiary.or") {
            return direct_multiary_or(fields["cols"])
        }
        if (op == "multiary.std") {
            return direct_multiary_std(fields["cols"], params["ddof"])
        }
        if (op == "multiary.var") {
            return direct_multiary_var(fields["cols"], params["ddof"])
        }
        if (op == "nullary.false") {
            return direct_nullary_false()
        }
        if (op == "nullary.literal") {
            return direct_nullary_literal(params["value"], params["dtype"])
        }
        if (op == "nullary.true") {
            return direct_nullary_true()
        }
        if (op == "ternary.where") {
            return direct_ternary_where(fields["condition"], fields["if_true"], fields["if_false"])
        }
        if (op == "unary.abs") {
            return direct_unary_abs(fields["col"])
        }
        if (op == "unary.acos") {
            return direct_unary_acos(fields["col"])
        }
        if (op == "unary.asin") {
            return direct_unary_asin(fields["col"])
        }
        if (op == "unary.atan") {
            return direct_unary_atan(fields["col"])
        }
        if (op == "unary.between") {
            return direct_unary_between(fields["col"], params["lower"], params["upper"], params["inclusive"])
        }
        if (op == "unary.cast") {
            return direct_unary_cast(fields["col"], params["dtype"])
        }
        if (op == "unary.ceil") {
            return direct_unary_ceil(fields["col"])
        }
        if (op == "unary.clip") {
            return direct_unary_clip(fields["col"], params["lower"], params["upper"])
        }
        if (op == "unary.cos") {
            return direct_unary_cos(fields["col"])
        }
        if (op == "unary.day") {
            return direct_unary_day(fields["col"])
        }
        if (op == "unary.day_of_year") {
            return direct_unary_day_of_year(fields["col"])
        }
        if (op == "unary.exp") {
            return direct_unary_exp(fields["col"])
        }
        if (op == "unary.expm1") {
            return direct_unary_expm1(fields["col"])
        }
        if (op == "unary.floor") {
            return direct_unary_floor(fields["col"])
        }
        if (op == "unary.get") {
            return direct_unary_get(fields["col"])
        }
        if (op == "unary.is_finite") {
            return direct_unary_is_finite(fields["col"])
        }
        if (op == "unary.is_month_end") {
            return direct_unary_is_month_end(fields["col"])
        }
        if (op == "unary.is_null") {
            return direct_unary_is_null(fields["col"])
        }
        if (op == "unary.is_quarter_end") {
            return direct_unary_is_quarter_end(fields["col"])
        }
        if (op == "unary.is_weekend") {
            return direct_unary_is_weekend(fields["col"])
        }
        if (op == "unary.is_year_end") {
            return direct_unary_is_year_end(fields["col"])
        }
        if (op == "unary.isin") {
            return direct_unary_isin(fields["col"], params["values"])
        }
        if (op == "unary.log") {
            return direct_unary_log(fields["col"])
        }
        if (op == "unary.log10") {
            return direct_unary_log10(fields["col"])
        }
        if (op == "unary.log1p") {
            return direct_unary_log1p(fields["col"])
        }
        if (op == "unary.log2") {
            return direct_unary_log2(fields["col"])
        }
        if (op == "unary.month") {
            return direct_unary_month(fields["col"])
        }
        if (op == "unary.neg") {
            return direct_unary_neg(fields["col"])
        }
        if (op == "unary.not") {
            return direct_unary_not(fields["col"])
        }
        if (op == "unary.not_null") {
            return direct_unary_not_null(fields["col"])
        }
        if (op == "unary.quarter") {
            return direct_unary_quarter(fields["col"])
        }
        if (op == "unary.replace") {
            return direct_unary_replace(fields["col"], params["old"], params["new"])
        }
        if (op == "unary.round") {
            return direct_unary_round(fields["col"], params["precision"])
        }
        if (op == "unary.sign") {
            return direct_unary_sign(fields["col"])
        }
        if (op == "unary.sin") {
            return direct_unary_sin(fields["col"])
        }
        if (op == "unary.sqrt") {
            return direct_unary_sqrt(fields["col"])
        }
        if (op == "unary.tan") {
            return direct_unary_tan(fields["col"])
        }
        if (op == "unary.week") {
            return direct_unary_week(fields["col"])
        }
        if (op == "unary.weekday") {
            return direct_unary_weekday(fields["col"])
        }
        if (op == "unary.year") {
            return direct_unary_year(fields["col"])
        }
        throw "未实现 DIRECT 算符 " + op
    }
    """,
)

EVALUATE_TIME_SERIES = DolphinDBFunction(
    module=MODULE,
    definition=r"""
    def evaluate_time_series(evaluator, source, definitions, mutable cache, mutable states, node) {
        // 解析 TS 节点，校验操作数后交由按 code、time 组织的时序执行上下文计算。
        op = node["op"]
        fields = evaluate_fields(evaluator, source, definitions, cache, states, node["fields"])
        params = node["params"]
        n = source.rows()
        code = require_column(source, "code", op)
        time = require_column(source, "time", op)
        on = NULL
        if ("on" in node) {
            on = evaluate_operand(evaluator, source, definitions, cache, states, node["on"])
        }

        if ("by" in node && type(node["by"]) != VOID) {
            by = evaluate_operand(evaluator, source, definitions, cache, states, node["by"])
            by = require_vector(by, n, op + ".by")
            valid_group = isValid(by)
            if (type(on) == VOID) on = valid_group
            else on = normalize_on(on, n) && valid_group
            if (n > 0) code = contextby(min, long(0 .. (n-1)), (code,by))
        }
        method = "ols"
        weights = NULL
        if ("method" in params) method = params["method"]
        if ("weights" in params && is_vector_form(params["weights"])) weights = double(params["weights"])
        if (op == "unary.rolling_mean" && type(weights) != VOID) {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = weighted_rolling_mean{,,params["window"],int(params["min_periods"]),weights}
            return apply_time_series(handler, (col,time), on, code, time, double([]))
        }
        binary_regression = op in ["binary.rolling_alpha", "binary.rolling_beta", "binary.rolling_residual", "binary.rolling_residual_std"]
        if (op in ["controls.rolling_alpha", "controls.rolling_beta", "controls.rolling_residual", "controls.rolling_residual_std"] ||
                (binary_regression && (method == "wls" || op == "binary.rolling_residual_std"))) {
            specification = dict(STRING, ANY)
            specification["fields"] = node["fields"]
            specification["window"] = params["window"]
            specification["minimum"] = rolling_min_periods(params["window"], int(params["min_periods"]))
            specification["method"] = method
            specification["weights"] = weights
            specification["binary"] = binary_regression
            specification["intercept"] = true
            if (!binary_regression) specification["intercept"] = params["intercept"]
            fill_config = dict(STRING, ANY)
            fill_config["rule"] = "ffill"
            if (binary_regression) fill_config["rule"] = NULL
            if ("fill" in params) fill_config["rule"] = params["fill"]
            control_count = 1
            if (!binary_regression) control_count = size(fields["controls"])
            specification["fill"] = normalize_regression_fill(fill_config["rule"], control_count)
            specification["on"] = NULL
            if ("on" in node) specification["on"] = node["on"]
            specification["by"] = NULL
            if ("by" in node) specification["by"] = node["by"]
            cache_key = "_query_rolling_ols_" + toStdJson(specification)
            for (attempt in 0 .. size(definitions)) {
                if (!(cache_key in definitions)) break
                cache_key = "_" + cache_key
            }
            if (!(cache_key in cache)) {
                control_values = array(ANY, 0)
                if (binary_regression) {
                    target = require_vector(fields["right"], n, op + ".fields.right")
                    control_values.append!(require_vector(fields["left"], n, op + ".fields.left"))
                } else {
                    target = require_vector(fields["target"], n, op + ".fields.target")
                    for (i in 0 .. (size(fields["controls"]) - 1))
                        control_values.append!(require_vector(fields["controls"][i], n, op + ".fields.controls"))
                }
                controls = build_control_table(control_values)
                cache[cache_key] = apply_rolling_ols(
                    target, controls, on, code, time, params["window"], int(params["min_periods"]),
                    specification["intercept"], specification["fill"], method, weights, binary_regression
                )
            }
            coefficients = cache[cache_key]
            if (op in ["controls.rolling_alpha", "binary.rolling_alpha"]) return coefficients.alpha
            if (op in ["controls.rolling_residual", "binary.rolling_residual"]) return coefficients.residual
            if (op in ["controls.rolling_residual_std", "binary.rolling_residual_std"]) return coefficients.residual_std
            index = 0
            if (!binary_regression && "index" in params) index = int(params["index"])
            name = "beta" + string(index)
            if (index < 0) throw "回归系数 index 必须是非负整数"
            if (!(name in coefficients.columnNames())) return take(double(NULL), n)
            return coefficients[name]
        }
        if ("window" in params && type(params["window"]) == STRING && !(op like "controls.%")) {
            operation = split(op, ".")[1]
            if (op like "binary.%") {
                left = require_vector(fields["left"], n, op + ".fields.left")
                right = require_vector(fields["right"], n, op + ".fields.right")
                handler = calendar_rolling_pair{,,, params["window"], int(params["min_periods"]), operation}
                return apply_time_series(handler, (left, right, time), on, code, time, double([]))
            }
            col = require_vector(fields["col"], n, op + ".fields.col")
            q = 0.5
            ascending = true
            ties_method = "min"
            if ("q" in params) q = params["q"]
            if ("ascending" in params) ascending = params["ascending"]
            if ("ties_method" in params) ties_method = params["ties_method"]
            handler = calendar_rolling_unary{,, params["window"], int(params["min_periods"]), operation, q, ascending, ties_method}
            empty = double([])
            if (op in ["unary.rolling_all", "unary.rolling_any"]) empty = bool([])
            return apply_time_series(handler, (col, time), on, code, time, empty)
        }
        if (op == "binary.cross_above") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_cross_above
            return apply_time_series(handler, (left, right), on, code, time, bool([]))
        }
        if (op == "binary.cross_below") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_cross_below
            return apply_time_series(handler, (left, right), on, code, time, bool([]))
        }
        if (op == "binary.ewm_corr") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_ewm_corr{,, double(params["com"]), double(params["span"]), double(params["half_life"]), double(params["alpha"]), params["min_periods"], params["adjust"], params["ignore_na"], params["bias"]}
            return apply_time_series(handler, (left, right), on, code, time, double([]))
        }
        if (op == "binary.ewm_cov") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_ewm_cov{,, double(params["com"]), double(params["span"]), double(params["half_life"]), double(params["alpha"]), params["min_periods"], params["adjust"], params["ignore_na"], params["bias"]}
            return apply_time_series(handler, (left, right), on, code, time, double([]))
        }
        if (op == "binary.expanding_beta") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_expanding_beta{,, params["min_periods"]}
            return apply_time_series(handler, (left, right), on, code, time, double([]))
        }
        if (op == "binary.expanding_corr") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_expanding_corr{,, params["min_periods"]}
            return apply_time_series(handler, (left, right), on, code, time, double([]))
        }
        if (op == "binary.expanding_cov") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_expanding_cov{,, params["min_periods"]}
            return apply_time_series(handler, (left, right), on, code, time, double([]))
        }
        if (op == "binary.rolling_alpha") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_rolling_alpha{,, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, (left, right), on, code, time, double([]))
        }
        if (op == "binary.rolling_beta") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_rolling_beta{,, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, (left, right), on, code, time, double([]))
        }
        if (op == "binary.rolling_corr") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_rolling_corr{,, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, (left, right), on, code, time, double([]))
        }
        if (op == "binary.rolling_cov") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_rolling_cov{,, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, (left, right), on, code, time, double([]))
        }
        if (op == "binary.rolling_residual") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = ts_binary_rolling_residual{,, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, (left, right), on, code, time, double([]))
        }
        if (op == "talib.ad") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            volume = require_vector(fields["volume"], n, op + ".fields.volume")
            handler = ts_talib_ad
            return apply_time_series(handler, (high, low, close, volume), on, code, time, double([]))
        }
        if (op == "talib.adx") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_adx{,,, params["time_period"]}
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.adxr") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_adxr{,,, params["time_period"]}
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.apo") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_apo{, params["fast_period"], params["slow_period"], params["ma_type"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.aroon") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            handler = ts_talib_aroon{,, params["time_period"], params["output"]}
            return apply_time_series(handler, (high, low), on, code, time, double([]))
        }
        if (op == "talib.aroonOsc") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            handler = ts_talib_aroonOsc{,, params["time_period"]}
            return apply_time_series(handler, (high, low), on, code, time, double([]))
        }
        if (op == "talib.atr") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_atr{,,, params["time_period"]}
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.avgPrice") {
            open = require_vector(fields["open"], n, op + ".fields.open")
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_avgPrice
            return apply_time_series(handler, (open, high, low, close), on, code, time, double([]))
        }
        if (op == "talib.bBands") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_bBands{, params["time_period"], params["nbdev_up"], params["nbdev_down"], params["ma_type"], params["output"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.beta") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            handler = ts_talib_beta{,, params["time_period"]}
            return apply_time_series(handler, (high, low), on, code, time, double([]))
        }
        if (op == "talib.bop") {
            open = require_vector(fields["open"], n, op + ".fields.open")
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_bop
            return apply_time_series(handler, (open, high, low, close), on, code, time, double([]))
        }
        if (op == "talib.cci") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_cci{,,, params["time_period"]}
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.correl") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            handler = ts_talib_correl{,, params["time_period"]}
            return apply_time_series(handler, (high, low), on, code, time, double([]))
        }
        if (op == "talib.dema") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_dema{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.dx") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_dx{,,, params["time_period"]}
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.ema") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_ema{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.kama") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_kama{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.linearreg") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_linearreg{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.linearreg_angle") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_linearreg_angle{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.linearreg_intercept") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_linearreg_intercept{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.linearreg_slope") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_linearreg_slope{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.ma") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_ma{, params["time_period"], params["ma_type"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.macd") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_macd{, params["fast_period"], params["slow_period"], params["signal_period"], params["output"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.medPrice") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            handler = ts_talib_medPrice
            return apply_time_series(handler, (high, low), on, code, time, double([]))
        }
        if (op == "talib.mfi") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            volume = require_vector(fields["volume"], n, op + ".fields.volume")
            handler = ts_talib_mfi{,,,, params["time_period"]}
            return apply_time_series(handler, (high, low, close, volume), on, code, time, double([]))
        }
        if (op == "talib.midPoint") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_midPoint{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.midPrice") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            handler = ts_talib_midPrice{,, params["time_period"]}
            return apply_time_series(handler, (high, low), on, code, time, double([]))
        }
        if (op == "talib.minus_di") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_minus_di{,,, params["time_period"]}
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.minus_dm") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            handler = ts_talib_minus_dm{,, params["time_period"]}
            return apply_time_series(handler, (high, low), on, code, time, double([]))
        }
        if (op == "talib.mom") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_mom{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.natr") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_natr{,,, params["time_period"]}
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.obv") {
            close = require_vector(fields["close"], n, op + ".fields.close")
            volume = require_vector(fields["volume"], n, op + ".fields.volume")
            handler = ts_talib_obv
            return apply_time_series(handler, (close, volume), on, code, time, double([]))
        }
        if (op == "talib.plus_di") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_plus_di{,,, params["time_period"]}
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.plus_dm") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            handler = ts_talib_plus_dm{,, params["time_period"]}
            return apply_time_series(handler, (high, low), on, code, time, double([]))
        }
        if (op == "talib.ppo") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_ppo{, params["fast_period"], params["slow_period"], params["ma_type"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.roc") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_roc{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.rocp") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_rocp{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.rocr") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_rocr{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.rocr100") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_rocr100{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.rsi") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_rsi{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.sma") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_sma{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.stddev") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_stddev{, params["time_period"], params["nbdev"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.t3") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_t3{, params["time_period"], params["vfactor"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.tema") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_tema{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.trange") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_trange
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.trima") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_trima{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.trix") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_trix{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.tsf") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_tsf{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.typPrice") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_typPrice
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.ultOsc") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_ultOsc{,,, params["period1"], params["period2"], params["period3"]}
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.var") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_var{, params["time_period"], params["nbdev"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "talib.wclPrice") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_wclPrice
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.willr") {
            high = require_vector(fields["high"], n, op + ".fields.high")
            low = require_vector(fields["low"], n, op + ".fields.low")
            close = require_vector(fields["close"], n, op + ".fields.close")
            handler = ts_talib_willr{,,, params["time_period"]}
            return apply_time_series(handler, (high, low, close), on, code, time, double([]))
        }
        if (op == "talib.wma") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_talib_wma{, params["time_period"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.bars_since") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_bars_since
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.bfill") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_bfill{, int(params["limit"])}
            return apply_time_series(handler, enlist(col), on, code, time, array(type(col), 0))
        }
        if (op == "unary.changed") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_changed{, params["null_equal"]}
            return apply_time_series(handler, enlist(col), on, code, time, bool([]))
        }
        if (op == "unary.consecutive_count") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_consecutive_count
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.cum_count") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_cum_count{, params["min_periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.cum_max") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_cum_max{, params["min_periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.cum_mean") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_cum_mean{, params["min_periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.cum_min") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_cum_min{, params["min_periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.cum_prod") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_cum_prod{, params["min_periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.cum_sum") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_cum_sum{, params["min_periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.decay_linear") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_decay_linear{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.diff") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_diff{, params["periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.ewm_mean") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_ewm_mean{, double(params["com"]), double(params["span"]), double(params["half_life"]), double(params["alpha"]), params["min_periods"], params["adjust"], params["ignore_na"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.ewm_std") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_ewm_std{, double(params["com"]), double(params["span"]), double(params["half_life"]), double(params["alpha"]), params["min_periods"], params["adjust"], params["ignore_na"], params["bias"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.ewm_var") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_ewm_var{, double(params["com"]), double(params["span"]), double(params["half_life"]), double(params["alpha"]), params["min_periods"], params["adjust"], params["ignore_na"], params["bias"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.expanding_median") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_expanding_median{, params["min_periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.expanding_quantile") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_expanding_quantile{, params["min_periods"], params["q"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.expanding_rank") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_expanding_rank{, params["min_periods"], params["ascending"], params["ties_method"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.expanding_rank_pct") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_expanding_rank_pct{, params["min_periods"], params["ascending"], params["ties_method"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.expanding_sem") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_expanding_sem{, params["min_periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.expanding_std") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_expanding_std{, params["min_periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.expanding_var") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_expanding_var{, params["min_periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.ffill") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_ffill{, int(params["limit"])}
            return apply_time_series(handler, enlist(col), on, code, time, array(type(col), 0))
        }
        if (op == "unary.log_return") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_log_return{, params["periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.pct_change") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_pct_change{, params["periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_all") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_all{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, bool([]))
        }
        if (op == "unary.rolling_any") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_any{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, bool([]))
        }
        if (op == "unary.rolling_argmax") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_argmax{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_argmin") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_argmin{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_count") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_count{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_first") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_first{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_kurt") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_kurt{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_last") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_last{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_mad") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_mad{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_max") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_max{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_mean") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_mean{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_median") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_median{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_min") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_min{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_prod") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_prod{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_quantile") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_quantile{, params["window"], int(params["min_periods"]), params["q"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_rank") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_rank{, params["window"], int(params["min_periods"]), params["ascending"], params["ties_method"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_rank_pct") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_rank_pct{, params["window"], int(params["min_periods"]), params["ascending"], params["ties_method"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_sem") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_sem{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_skew") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_skew{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_std") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_std{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_sum") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_sum{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_true_count") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_true_count{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_var") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_var{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.rolling_zscore") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_rolling_zscore{, params["window"], int(params["min_periods"])}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        if (op == "unary.shift") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = ts_unary_shift{, params["periods"]}
            return apply_time_series(handler, enlist(col), on, code, time, double([]))
        }
        throw "未实现 TS 算符 " + op
    }
    """,
    dependencies=(CALENDAR_ROLLING_PAIR, CALENDAR_ROLLING_UNARY, WEIGHTED_ROLLING_MEAN),
)

EVALUATE_CROSS_SECTION = DolphinDBFunction(
    module=MODULE,
    definition=r"""
    def evaluate_cross_section(evaluator, source, definitions, mutable cache, mutable states, node) {
        // 解析 CS 节点，并根据普通、分组或控制变量字段选择对应截面执行上下文。
        op = node["op"]
        fields = evaluate_fields(evaluator, source, definitions, cache, states, node["fields"])
        params = node["params"]
        n = source.rows()
        time = require_column(source, "time", op)
        on = NULL
        if ("on" in node) {
            on = evaluate_operand(evaluator, source, definitions, cache, states, node["on"])
        }

        if (op == "binary.alpha") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = cs_binary_alpha
            return apply_cross_section(handler, (left, right), on, time, double([]))
        }
        if (op == "binary.beta") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = cs_binary_beta
            return apply_cross_section(handler, (left, right), on, time, double([]))
        }
        if (op == "binary.corr") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = cs_binary_corr
            return apply_cross_section(handler, (left, right), on, time, double([]))
        }
        if (op == "binary.cov") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = cs_binary_cov
            return apply_cross_section(handler, (left, right), on, time, double([]))
        }
        if (op == "binary.rank_corr") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = cs_binary_rank_corr
            return apply_cross_section(handler, (left, right), on, time, double([]))
        }
        if (op == "binary.residual") {
            left = require_vector(fields["left"], n, op + ".fields.left")
            right = require_vector(fields["right"], n, op + ".fields.right")
            handler = cs_binary_residual
            return apply_cross_section(handler, (left, right), on, time, double([]))
        }
        if (op in ["controls.alpha", "controls.beta", "controls.residual"]) {
            target = require_vector(fields["target"], n, op + ".fields.target")
            control_values = fields["controls"]
            normalized_controls = array(ANY, 0)
            for (index in 0..(size(control_values) - 1)) {
                normalized_controls.append!(
                    require_vector(
                        control_values[index],
                        n,
                        op + ".fields.controls[" + string(index) + "]"
                    )
                )
            }
            controls = build_control_table(normalized_controls)
            if (op == "controls.alpha") handler = cs_controls_alpha{,, params["intercept"]}
            else if (op == "controls.beta") handler = cs_controls_beta{,, params["intercept"], params["index"]}
            else handler = cs_controls_residual{,, params["intercept"]}
            return apply_controlled_cross_section(handler, target, controls, on, time)
        }
        if (op == "grouped.demean") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            by = require_vector(fields["by"], n, op + ".fields.by")
            handler = cs_grouped_demean
            return apply_grouped_cross_section(handler, enlist(col), on, time, by, double([]))
        }
        if (op == "grouped.mean") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            by = require_vector(fields["by"], n, op + ".fields.by")
            handler = cs_grouped_mean
            return apply_grouped_cross_section(handler, enlist(col), on, time, by, double([]))
        }
        if (op == "grouped.rank_pct") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            by = require_vector(fields["by"], n, op + ".fields.by")
            handler = cs_grouped_rank_pct{, params["ascending"], params["ties_method"]}
            return apply_grouped_cross_section(handler, enlist(col), on, time, by, double([]))
        }
        if (op == "grouped.zscore") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            by = require_vector(fields["by"], n, op + ".fields.by")
            handler = cs_grouped_zscore{, params["ddof"]}
            return apply_grouped_cross_section(handler, enlist(col), on, time, by, double([]))
        }
        if (op == "unary.bottom_n") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_bottom_n{, params["n"]}
            return apply_cross_section(handler, enlist(col), on, time, bool([]))
        }
        if (op == "unary.bottom_pct") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_bottom_pct{, params["pct"]}
            return apply_cross_section(handler, enlist(col), on, time, bool([]))
        }
        if (op == "unary.count") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_count
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.demean") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_demean
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.kurt") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_kurt
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.mad") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_mad
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.max") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_max
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.mean") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_mean
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.median") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_median
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.min") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_min
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.normalize_l1") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_normalize_l1
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.normalize_l2") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_normalize_l2
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.normalize_sum") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_normalize_sum
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.qcut") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_qcut{, params["q"]}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.quantile") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            interpolation = "linear"
            if ("interpolation" in params) interpolation = params["interpolation"]
            handler = cs_unary_quantile{, params["q"], interpolation}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.rank") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_rank{, params["ascending"], params["ties_method"]}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.rank_dense") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_rank_dense{, params["ascending"]}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.rank_normal") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_rank_normal{, params["ascending"]}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.rank_pct") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_rank_pct{, params["ascending"], params["ties_method"]}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.robust_zscore") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_robust_zscore{, params["scale"]}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.skew") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_skew
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.std") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_std{, params["ddof"]}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.sum") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_sum
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.top_n") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_top_n{, params["n"]}
            return apply_cross_section(handler, enlist(col), on, time, bool([]))
        }
        if (op == "unary.top_pct") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_top_pct{, params["pct"]}
            return apply_cross_section(handler, enlist(col), on, time, bool([]))
        }
        if (op == "unary.var") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_var{, params["ddof"]}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.winsorize") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_winsorize{, params["lower"], params["upper"]}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.winsorize_mad") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_winsorize_mad{, params["n"], params["scale"]}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        if (op == "unary.zscore") {
            col = require_vector(fields["col"], n, op + ".fields.col")
            handler = cs_unary_zscore{, params["ddof"]}
            return apply_cross_section(handler, enlist(col), on, time, double([]))
        }
        throw "未实现 CS 算符 " + op
    }
    """,
)

EVALUATOR_FUNCTIONS = (
    EVALUATE_DIRECT,
    EVALUATE_TIME_SERIES,
    EVALUATE_CROSS_SECTION,
)
