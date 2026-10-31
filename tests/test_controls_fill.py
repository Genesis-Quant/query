"""Configurable TS-controls fill matches independent per-column pandas/NumPy references."""

import json
import os

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from query import FactorQuery, create_session
from query.database.compile.common.functions import (
    FILL_REGRESSION_COLUMN,
    FILL_REGRESSION_INPUTS,
    NORMALIZE_REGRESSION_FILL,
)

OPERATIONS = ("controls.rolling_alpha", "controls.rolling_beta", "controls.rolling_residual")
OMITTED = object()


def definition(operation="controls.rolling_residual", *, fill=OMITTED, controls=("x", "z"), **params):
    parameters = {"window": 6, "min_periods": 3, **params}
    if fill is not OMITTED:
        parameters["fill"] = fill
    return {"type": "TS", "op": operation,
            "fields": {"target": "target", "controls": list(controls)}, "params": parameters}


def request(derivatives):
    return {"start_date": "2025-01-01", "end_date": "2025-12-31", "codes": ["A", "B"],
            "derivatives": derivatives}


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("fill", [
    OMITTED, None, "ffill", "mean", {}, {"method": "ffill"}, {"method": "mean"},
    {"method": "constant", "value": 0.0},
    {"target": None}, {"controls": None},
    {"target": {"method": "constant", "value": 0}, "controls": ["ffill", None]},
    {"target": "mean", "controls": [None, {"method": "mean"}]},
])
def test_fill_schema_defaults_and_json_round_trip(operation, fill):
    model = FactorQuery.model_validate(request({"result": definition(operation, fill=fill)}))
    if fill is OMITTED:
        assert model.derivatives["result"].params.fill == "ffill"
    assert FactorQuery.model_validate_json(model.model_dump_json()) == model
    assert model.source_factors() == ["target", "x", "z"]


@pytest.mark.parametrize("fill", [
    "constant", "bfill", "median", "None", 0, True, [],
    {"method": "constant"}, {"method": "constant", "value": None}, {"method": "constant", "value": ""},
    {"method": "constant", "value": np.inf}, {"method": "constant", "value": np.nan},
    {"method": "mean", "value": 1.0}, {"method": "ffill", "value": "x"},
    {"method": "mean", "target": None}, {"method": "ffill", "limit": 2},
    {"unknown": 1}, {"controls": []}, {"controls": [None]},
    {"controls": [None, None, None]}, {"controls": "ffill"},
    {"target": {"method": "constant", "value": 0, "extra": True}},
])
def test_invalid_fill_contracts_are_rejected(fill):
    with pytest.raises(ValidationError):
        FactorQuery.model_validate(request({"result": definition(fill=fill)}))


def test_fill_helpers_belong_to_common_only():
    for function in (NORMALIZE_REGRESSION_FILL, FILL_REGRESSION_COLUMN, FILL_REGRESSION_INPUTS):
        assert function.module == "common"
    assert FILL_REGRESSION_INPUTS.parameters == ("target", "controls", "code", "time", "fill")


@pytest.fixture(scope="module")
def dolphin():
    if os.getenv("QUERY_TEST_DOLPHINDB") != "1":
        pytest.skip("requires explicit opt-in to the configured DolphinDB server")
    session = create_session(max_time=300)
    try:
        yield session
    finally:
        session.close()


def source():
    rng = np.random.default_rng(275)
    dates = pd.bdate_range("2025-01-02", periods=24)
    count = len(dates)
    stocks = 6
    x = np.tile(rng.normal(size=count), stocks)
    z = rng.normal(size=stocks * count)
    y = 0.4 + 1.2 * x - 0.7 * z + rng.normal(scale=0.15, size=stocks * count)
    frame = pd.DataFrame({
        "time": np.tile(dates.to_numpy(), stocks),
        "code": np.repeat([f"S{i}" for i in range(stocks)], count),
        "target": y, "x": x, "z": z,
        "category": np.tile(np.array(["bank", "retail", "tech"])[np.arange(count) // 5 % 3], stocks),
        "flag": np.tile(np.arange(count) % 2 == 0, stocks),
        "selected": True,
    })
    day = frame.groupby("code").cumcount()
    stock = frame.code.str[1:].astype(int)
    frame.loc[(day + stock) % 11 == 0, "target"] = np.nan
    frame.loc[(day * 2 + stock) % 13 == 0, "x"] = np.nan
    frame.loc[(day * 3 + stock) % 17 == 0, "z"] = np.nan
    frame.loc[(day == 9) | ((day + stock) % 19 == 0), "category"] = None
    frame.loc[(day + stock) % 10 == 0, "selected"] = False
    frame.loc[(day == 6) & (stock == 2), "target"] = np.inf
    frame.loc[(day == 10) & (stock == 1), "x"] = -np.inf
    return frame


def fill_rules(fill, controls):
    if fill is OMITTED:
        fill = "ffill"
    if isinstance(fill, dict) and "method" not in fill:
        target = fill.get("target", "ffill")
        rules = fill.get("controls")
        return [target, *(["ffill"] * len(controls) if rules is None else rules)]
    return [fill] * (len(controls) + 1)


def filled_reference(frame, controls, fill, *, on=False):
    result = frame.copy()
    selected = result.selected.fillna(False).astype(bool) if on else pd.Series(True, index=result.index)
    participants = result.loc[selected].sort_values(["code", "time"], kind="stable")
    for name, rule in zip(["target", *controls], fill_rules(fill, controls), strict=True):
        if rule is None:
            continue
        method = rule["method"] if isinstance(rule, dict) else rule
        values = participants[name].copy()
        if pd.api.types.is_numeric_dtype(values) and not pd.api.types.is_bool_dtype(values):
            values = values.where(np.isfinite(values), np.nan)
        if method == "constant":
            values = values.fillna(rule["value"])
        elif method == "ffill":
            values = values.groupby(participants.code, sort=False).ffill()
        elif method == "mean":
            means = values.groupby(participants.time, sort=False).transform("mean")
            values = values.fillna(means)
        result.loc[participants.index, name] = values
    return result


def reference(frame, controls, fill, *, window=6, minimum=3, intercept=True, on=False, betas=6):
    frame = filled_reference(frame, controls, fill, on=on)
    output = pd.DataFrame(np.nan, index=frame.index,
                          columns=["alpha", "residual", *[f"beta{i}" for i in range(betas)]])
    for _, stock in frame.groupby("code", sort=False):
        stock = stock.sort_values("time", kind="stable")
        if on:
            stock = stock.loc[stock.selected.fillna(False)]
        for index in range(len(stock)):
            sample = stock.iloc[max(0, index - window + 1):index + 1]
            valid = np.isfinite(sample.target.to_numpy(dtype=float))
            categorical = []
            for name in controls:
                category = not pd.api.types.is_numeric_dtype(sample[name]) or pd.api.types.is_bool_dtype(sample[name])
                categorical.append(category)
                valid &= sample[name].notna().to_numpy() if category else np.isfinite(sample[name].to_numpy(dtype=float))
            if valid.sum() < minimum:
                continue
            clean = sample.loc[valid]
            y = clean.target.to_numpy(dtype=float)
            columns = []
            for name, category in zip(controls, categorical, strict=True):
                if category:
                    for level in sorted(clean[name].unique())[1:]:
                        columns.append((clean[name] == level).to_numpy(dtype=float))
                else:
                    columns.append(clean[name].to_numpy(dtype=float))
            active = [j for j, values in enumerate(columns) if len(np.unique(values)) > 1]
            beta = np.zeros(len(columns))
            alpha = y.mean()
            last_error = sample.target.iloc[-1] - alpha if valid[-1] else np.nan
            if active and len(y) > 1 and len(y) > len(active) + int(intercept):
                design = np.column_stack([columns[j] for j in active])
                if intercept:
                    design = np.column_stack([np.ones(len(y)), design])
                coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
                alpha = coefficients[0] if intercept else 0.0
                beta[active] = coefficients[int(intercept):]
                last_error = y[-1] - design[-1] @ coefficients if valid[-1] else np.nan
            row = stock.index[index]
            output.loc[row, "alpha"] = alpha
            output.loc[row, "residual"] = last_error
            for j in range(min(betas, len(beta))):
                output.loc[row, f"beta{j}"] = beta[j]
    return output


def evaluate(session, frame, controls, fill=OMITTED, *, on=False, window=6, minimum=3, intercept=True, betas=6):
    derivatives = {
        "alpha": definition(OPERATIONS[0], controls=controls, fill=fill, window=window, min_periods=minimum, intercept=intercept),
        "residual": definition(OPERATIONS[2], controls=controls, fill=fill, window=window, min_periods=minimum, intercept=intercept),
    }
    for index in range(betas):
        derivatives[f"beta{index}"] = definition(OPERATIONS[1], controls=controls, fill=fill, window=window,
                                                min_periods=minimum, intercept=intercept, index=index)
    if on:
        for node in derivatives.values():
            node["on"] = {"type": "DIRECT", "op": "binary.eq", "fields": {"left": "selected", "right": True}}
    model = FactorQuery.model_validate(request(derivatives))
    nodes = {name: node.model_dump(mode="json") for name, node in model.derivatives.items()}
    session.upload({"fillTestSource": frame, "fillTestDefinitions": json.dumps(nodes)})
    session.run("fillTestOriginal=fillTestSource.copy();NULL")
    actual = session.run("compute_factors(fillTestSource,fromStdJson(fillTestDefinitions))")
    assert session.run('''
        fillTestUnchanged=true
        for(fillTestName in fillTestOriginal.columnNames())
            fillTestUnchanged=fillTestUnchanged && eqObj(fillTestSource[fillTestName],fillTestOriginal[fillTestName])
        fillTestUnchanged
    ''')
    return actual


@pytest.mark.parametrize("intercept", [False, True])
@pytest.mark.parametrize("on", [False, True])
@pytest.mark.parametrize("fill", [
    OMITTED, None, "ffill", "mean", {"method": "constant", "value": 0.0},
    {"target": None}, {"target": {"method": "constant", "value": -0.2}, "controls": ["mean", "ffill"]},
    {"target": "mean", "controls": [None, {"method": "constant", "value": 0.3}]},
])
def test_each_fill_matches_independent_numeric_reference(dolphin, intercept, on, fill):
    frame = source().sample(frac=1, random_state=8).reset_index(drop=True)
    actual = evaluate(dolphin, frame, ["x", "z"], fill, intercept=intercept, on=on)
    expected = reference(frame, ["x", "z"], fill, intercept=intercept, on=on)
    np.testing.assert_allclose(actual[expected.columns], expected, atol=1e-10, rtol=1e-7, equal_nan=True)
    for name in ("target", "x", "z", "category"):
        expected_column = frame[name].fillna("") if name == "category" else frame[name].replace([np.inf, -np.inf], np.nan)
        pd.testing.assert_series_equal(actual[name], expected_column)


@pytest.mark.parametrize("fill", [
    OMITTED, None,
    {"target": None, "controls": ["ffill", "ffill", "ffill"]},
    {"target": "mean", "controls": ["mean", {"method": "constant", "value": "missing"}, "ffill"]},
])
def test_categorical_inputs_keep_encoding_and_type(dolphin, fill):
    frame = source()
    controls = ["x", "category", "flag"]
    actual = evaluate(dolphin, frame, controls, fill)
    expected = reference(frame, controls, fill)
    np.testing.assert_allclose(actual[expected.columns], expected, atol=1e-10, rtol=1e-7, equal_nan=True)


def test_default_and_explicit_ffill_match_and_none_retains_missing_current_residual(dolphin):
    frame = source()
    frame.loc[frame.groupby("code").cumcount().eq(23), "target"] = np.nan
    default = evaluate(dolphin, frame, ["x", "z"])
    explicit = evaluate(dolphin, frame, ["x", "z"], "ffill")
    disabled = evaluate(dolphin, frame, ["x", "z"], None)
    names = ["alpha", "residual", "beta0", "beta1"]
    np.testing.assert_allclose(default[names], explicit[names], atol=1e-12, equal_nan=True)
    last = frame.index[frame.groupby("code").cumcount().eq(23)]
    assert default.loc[last, "residual"].notna().all()
    assert disabled.loc[last, "residual"].isna().all()


def test_ffill_is_stock_local_no_future_and_can_use_loaded_rows_before_window(dolphin):
    frame = source()
    day = frame.groupby("code").cumcount()
    frame.loc[day.lt(2), ["target", "x", "z"]] = np.nan
    frame.loc[frame.code.eq("S0") & day.ge(4), "x"] = np.nan
    full = evaluate(dolphin, frame, ["x", "z"], "ffill")
    expected = reference(frame, ["x", "z"], "ffill")
    np.testing.assert_allclose(full[expected.columns], expected, atol=1e-10, equal_nan=True)
    assert full.loc[day.lt(2), ["alpha", "residual", "beta0", "beta1"]].isna().all().all()
    assert full.loc[frame.code.eq("S0") & day.ge(12), "residual"].notna().all()
    prefix = frame.loc[day.le(13)].reset_index(drop=True)
    truncated = evaluate(dolphin, prefix, ["x", "z"], "ffill")
    np.testing.assert_allclose(full.loc[day.le(13), expected.columns], truncated[expected.columns],
                               atol=1e-10, equal_nan=True)


def test_mean_uses_same_date_raw_participants_and_leaves_empty_cross_sections(dolphin):
    frame = source()
    day = frame.groupby("code").cumcount()
    frame.loc[day.eq(4), "target"] = np.nan
    frame.loc[frame.code.eq("S0") & day.eq(7), "target"] = 1000000.0
    frame.loc[frame.code.eq("S0") & day.eq(7), "selected"] = False
    frame.loc[frame.code.eq("S1") & day.eq(7), "target"] = np.nan
    actual = evaluate(dolphin, frame, ["x", "z"], "mean", on=True)
    expected = reference(frame, ["x", "z"], "mean", on=True)
    np.testing.assert_allclose(actual[expected.columns], expected, atol=1e-10, equal_nan=True)
    assert actual.loc[day.eq(4), "residual"].isna().all()
    assert actual.loc[~frame.selected, expected.columns].isna().all().all()


@pytest.mark.parametrize("category", ["category", "flag"])
def test_mean_rejects_categorical_controls(dolphin, category):
    with pytest.raises(RuntimeError, match="mean.*分类"):
        evaluate(dolphin, source(), [category], "mean")


@pytest.mark.parametrize("value", [True, "invalid"])
def test_numeric_target_rejects_wrong_constant_types(dolphin, value):
    fill = {"target": {"method": "constant", "value": value}, "controls": [None, None]}
    with pytest.raises(RuntimeError, match="constant.*数值"):
        evaluate(dolphin, source(), ["x", "z"], fill)


@pytest.mark.parametrize("fill", [None, "ffill", "mean", {"method": "constant", "value": 0.0}])
def test_empty_and_all_missing_panels(dolphin, fill):
    frame = source()
    frame[["target", "x", "z"]] = np.nan
    actual = evaluate(dolphin, frame, ["x", "z"], fill)
    expected = reference(frame, ["x", "z"], fill)
    np.testing.assert_allclose(actual[expected.columns], expected, atol=1e-10, equal_nan=True)
    empty = evaluate(dolphin, frame.iloc[:0], ["x", "z"], fill)
    assert empty.empty
    assert {"alpha", "residual", "beta0", "beta1"} <= set(empty.columns)


def test_constant_does_not_remove_window_warmup(dolphin):
    frame = source()
    actual = evaluate(dolphin, frame, ["x", "z"], {"method": "constant", "value": 0.0}, minimum=6)
    for _, stock in frame.groupby("code"):
        assert actual.loc[stock.index[:5], ["alpha", "residual", "beta0", "beta1"]].isna().all().all()


@pytest.mark.parametrize("kind", ["bool", "string", "symbol"])
@pytest.mark.parametrize("method", ["ffill", "constant", None])
def test_categorical_fill_preserves_storage_type_and_nulls(dolphin, kind, method):
    literals = {"bool": "bool([true,NULL,false,NULL])",
                "string": '["bank","","tech",""]',
                "symbol": 'symbol(["bank","","tech",""])'}
    constants = {"bool": "false", "string": '"unknown"', "symbol": '"unknown"'}
    mode = '""' if method is None else f'"{method}"'
    dolphin.run(f'fillTestColumn={literals[kind]};fillTestColumnCopy=fillTestColumn.copy();NULL')
    before_type = dolphin.run("type(fillTestColumn)")
    actual = dolphin.run(f'fill_regression_column(fillTestColumn,{mode},{constants[kind]},take("A",4),1..4,false)')
    actual_type = dolphin.run(f'type(fill_regression_column(fillTestColumn,{mode},{constants[kind]},take("A",4),1..4,false))')
    assert before_type == actual_type
    assert dolphin.run("eqObj(fillTestColumn,fillTestColumnCopy)")
    if kind == "bool":
        expected = {None: [True, None, False, None], "ffill": [True, True, False, False],
                    "constant": [True, False, False, False]}[method]
    else:
        expected = {None: ["bank", "", "tech", ""], "ffill": ["bank", "bank", "tech", "tech"],
                    "constant": ["bank", "unknown", "tech", "unknown"]}[method]
    assert list(actual) == expected


@pytest.mark.parametrize("kind,value", [("bool", 0), ("bool", "false"), ("string", 0), ("symbol", False)])
def test_categorical_constant_rejects_wrong_types(dolphin, kind, value):
    literal = 'true false true' if kind == "bool" else ('symbol(["bank","tech","bank"])' if kind == "symbol" else '["bank","tech","bank"]')
    dolphin.upload({"fillTestWrongConstant": value})
    with pytest.raises(RuntimeError, match="constant 必须"):
        dolphin.run(f'fill_regression_column({literal},"constant",fillTestWrongConstant,take("A",3),1..3,false)')


@pytest.mark.parametrize("fill", [OMITTED, None, "ffill", "mean",
                                    {"target": "mean", "controls": [{"method": "constant", "value": "unknown"}]}])
def test_symbol_control_dsl_matches_string_control(dolphin, fill):
    frame = source()
    derivatives = {"as_symbol": {"type": "DIRECT", "op": "unary.cast", "fields": {"col": "category"}, "params": {"dtype": "symbol"}}}
    for name, operation in zip(["alpha", "beta", "residual"], OPERATIONS, strict=True):
        derivatives["string_" + name] = definition(operation, controls=["category"], fill=fill)
        derivatives["symbol_" + name] = definition(operation, controls=["as_symbol"], fill=fill)
    model = FactorQuery.model_validate(request(derivatives))
    dolphin.upload({"fillTestSource": frame, "fillTestDefinitions": json.dumps({name: node.model_dump(mode="json") for name, node in model.derivatives.items()})})
    if fill == "mean":
        with pytest.raises(RuntimeError, match="mean.*分类"):
            dolphin.run("compute_factors(fillTestSource,fromStdJson(fillTestDefinitions))")
        return
    actual = dolphin.run("compute_factors(fillTestSource,fromStdJson(fillTestDefinitions))")
    for name in ("alpha", "beta", "residual"):
        np.testing.assert_allclose(actual["string_" + name], actual["symbol_" + name], atol=1e-10, equal_nan=True)


@pytest.mark.parametrize("fill", [None, "ffill", "mean", {"method": "constant", "value": 0.0}])
def test_public_single_sequence_functions_apply_fill(dolphin, fill):
    frame = source().loc[lambda values: values.code.eq("S2")].reset_index(drop=True)
    actual = evaluate(dolphin, frame, ["x", "z"], fill, betas=2)
    dolphin.upload({"fillTestRule": json.dumps(fill)})
    dolphin.run("fillTestControls=table(fillTestSource.x as x,fillTestSource.z as z);NULL")
    for suffix, name, extra in [("alpha", "alpha", ""), ("beta", "beta0", ",0"),
                                ("beta", "beta1", ",1"), ("residual", "residual", "")]:
        rule = "NULL" if fill is None else "fromStdJson(fillTestRule)"
        direct = dolphin.run(f"ts_controls_rolling_{suffix}(fillTestSource.target,fillTestControls,6,3,true{extra},{rule})")
        np.testing.assert_allclose(direct, actual[name], atol=1e-10, equal_nan=True)


def test_old_positional_dos_calls_use_ffill_default(dolphin):
    dolphin.run('fillTestTarget=1.0 NULL 3 4 6 8;fillTestControls=table(1.0 2 3 NULL 5 6 as x);NULL')
    for suffix, extra in [("alpha", ""), ("beta", ",0"), ("residual", "")]:
        args = f"fillTestTarget,fillTestControls,4,3,true{extra}"
        omitted = dolphin.run(f"ts_controls_rolling_{suffix}({args})")
        explicit = dolphin.run(f'ts_controls_rolling_{suffix}({args},"ffill")')
        np.testing.assert_allclose(omitted, explicit, atol=1e-12, equal_nan=True)


def test_normalized_fill_cache_separates_methods_and_shares_equivalent_defaults(dolphin):
    derivatives = {
        "default": definition(OPERATIONS[0]),
        "string": definition(OPERATIONS[1], fill="ffill"),
        "rule": definition(OPERATIONS[2], fill={"method": "ffill"}),
        "columns": definition(OPERATIONS[1], fill={"target": "ffill", "controls": ["ffill", "ffill"]}, index=1),
        "disabled": definition(OPERATIONS[2], fill=None),
        "mean": definition(OPERATIONS[2], fill="mean"),
        "zero": definition(OPERATIONS[2], fill={"method": "constant", "value": 0.0}),
        "one": definition(OPERATIONS[2], fill={"method": "constant", "value": 1.0}),
    }
    model = FactorQuery.model_validate(request(derivatives))
    dolphin.upload({"fillTestSource": source(), "fillTestDefinitions": json.dumps({name: node.model_dump(mode="json") for name, node in model.derivatives.items()})})
    keys = dolphin.run('''
        fillTestParsed=fromStdJson(fillTestDefinitions)
        fillTestCache=dict(STRING,ANY)
        fillTestStates=dict(STRING,INT)
        for(name in string(fillTestParsed.keys()))
            evaluate_definition(evaluate_node,fillTestSource,fillTestParsed,fillTestCache,fillTestStates,name)
        string(fillTestCache.keys())
    ''')
    assert sum(str(key).startswith("_query_rolling_ols_") for key in keys) == 5
    actual = dolphin.run("compute_factors(fillTestSource,fromStdJson(fillTestDefinitions))")
    for name, fill in [("disabled", None), ("mean", "mean"), ("zero", {"method": "constant", "value": 0.0}),
                       ("one", {"method": "constant", "value": 1.0})]:
        expected = reference(source(), ["x", "z"], fill)
        np.testing.assert_allclose(actual[name], expected.residual, atol=1e-10, equal_nan=True)


def test_fill_then_batch_matches_prefilled_single_stock_regression(dolphin):
    frame = source()
    for fill in (None, "ffill", "mean", {"method": "constant", "value": 0.0}):
        expected_inputs = filled_reference(frame, ["x", "z"], fill)
        actual = evaluate(dolphin, frame, ["x", "z"], fill)
        prefilled = evaluate(dolphin, expected_inputs, ["x", "z"], None)
        names = ["alpha", "residual", "beta0", "beta1"]
        np.testing.assert_allclose(actual[names], prefilled[names], atol=1e-10, equal_nan=True)


def test_ffill_and_mean_respect_nullable_on_and_never_fill_output_rows(dolphin):
    frame = source()
    frame["selected"] = True
    frame.loc[[7, 31, 55], "selected"] = False
    for method in ("ffill", "mean"):
        derivatives = {name: definition(operation, fill=method) for name, operation in zip(["alpha", "beta", "residual"], OPERATIONS, strict=True)}
        for node in derivatives.values():
            node["on"] = {"type": "DIRECT", "op": "binary.eq", "fields": {"left": "selected", "right": True}}
        model = FactorQuery.model_validate(request(derivatives))
        dolphin.upload({"fillTestSource": frame, "fillTestDefinitions": json.dumps({name: node.model_dump(mode="json") for name, node in model.derivatives.items()})})
        dolphin.run('fillTestOn=fillTestSource.selected;fillTestOn[7 31 55]=bool(NULL);fillTestSource["selected"]=fillTestOn;NULL')
        actual = dolphin.run("compute_factors(fillTestSource,fromStdJson(fillTestDefinitions))")
        expected = reference(frame, ["x", "z"], method, on=True)
        np.testing.assert_allclose(actual[["alpha", "residual"]], expected[["alpha", "residual"]], atol=1e-10, equal_nan=True)
        assert actual.loc[[7, 31, 55], ["alpha", "beta", "residual"]].isna().all().all()


@pytest.mark.parametrize("dtype", ["int", "long", "float", "double"])
@pytest.mark.parametrize("method", ["ffill", "constant", "mean"])
def test_numeric_fill_can_produce_fractional_values_without_truncation(dolphin, dtype, method):
    dolphin.run(f'fillTestNumeric={dtype}(1 NULL 3 4);NULL')
    actual = dolphin.run(f'fill_regression_column(fillTestNumeric,"{method}",2.5,`A`B`A`B,1 1 2 2,true)')
    expected = {"ffill": [1, np.nan, 3, 4], "constant": [1, 2.5, 3, 4], "mean": [1, 1, 3, 4]}[method]
    np.testing.assert_allclose(actual, expected, atol=1e-12, equal_nan=True)
    assert dolphin.run(f'type(fill_regression_column(fillTestNumeric,"{method}",2.5,`A`B`A`B,1 1 2 2,true))') == 16
    if method == "constant":
        inputs = dolphin.run('fill_regression_inputs(fillTestNumeric,table(fillTestNumeric as x),`A`B`A`B,1 1 2 2,fromStdJson("{\\"method\\":\\"constant\\",\\"value\\":2.5}"))')
        np.testing.assert_allclose(inputs["target"], expected, atol=1e-12)
        np.testing.assert_allclose(inputs["controls"].x, expected, atol=1e-12)


def test_mixed_typed_column_rules_do_not_coerce_constants(dolphin):
    fill = {"target": {"method": "constant", "value": 0.0},
            "controls": [{"method": "constant", "value": False},
                         {"method": "constant", "value": "unknown"}, None, "mean"]}
    dolphin.upload({"fillTestMixedRule": json.dumps(fill)})
    result = dolphin.run('''
        fill_regression_inputs(1.0 NULL 3,
            table(bool([true,NULL,false]) as flag,["a","","b"] as category,
                  1.0 NULL 3 as unchanged,1.0 2 NULL as number),
            take("A",3),1..3,fromStdJson(fillTestMixedRule))
    ''')
    np.testing.assert_allclose(result["target"], [1, 0, 3])
    assert list(result["controls"].flag) == [True, False, False]
    assert list(result["controls"].category) == ["a", "unknown", "b"]
    np.testing.assert_allclose(result["controls"].unchanged, [1, np.nan, 3], equal_nan=True)
    np.testing.assert_allclose(result["controls"].number, [1, 2, np.nan], equal_nan=True)


@pytest.mark.parametrize("fill", ["ffill", "mean", {"method": "constant", "value": 0.0}])
def test_duplicate_dates_and_absent_rows_keep_stable_window_order(dolphin, fill):
    frame = source()
    day = frame.groupby("code").cumcount()
    stock = frame.code.str[1:].astype(int)
    frame = frame.loc[(day + stock) % 7 != 0].copy()
    frame.loc[frame.time.eq(pd.Timestamp("2025-01-10")), "time"] = pd.Timestamp("2025-01-09")
    frame = frame.sample(frac=1, random_state=19).reset_index(drop=True)
    actual = evaluate(dolphin, frame, ["x", "z"], fill)
    expected = reference(frame, ["x", "z"], fill)
    np.testing.assert_allclose(actual[expected.columns], expected, atol=1e-10, equal_nan=True)


def test_explicit_none_for_every_column_matches_global_none(dolphin):
    frame = source()
    default = evaluate(dolphin, frame, ["x", "z"], None)
    per_column = evaluate(dolphin, frame, ["x", "z"], {"target": None, "controls": [None, None]})
    names = ["alpha", "residual", "beta0", "beta1"]
    np.testing.assert_allclose(default[names], per_column[names], atol=1e-12, equal_nan=True)
