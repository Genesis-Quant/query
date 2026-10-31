"""The panel batching path preserves the published scalar-window regression contract."""

import json
import os

import numpy as np
import pandas as pd
import pytest

from query import FactorQuery, create_session
from query.database.compile.common.functions import (
    CONTROLS_REGRESSION_BATCH,
    ROLLING_CONTROLS_REGRESSION,
)


@pytest.fixture(scope="module")
def dolphin():
    if os.getenv("QUERY_TEST_DOLPHINDB") != "1":
        pytest.skip("requires explicit opt-in to the configured DolphinDB server")
    session = create_session(max_time=300)
    session.run('''
        def batchTestLegacy(target,controls,on,code,time,window,minimum,intercept) {
            n=size(target)
            output=dict(STRING,ANY)
            output["alpha"]=take(double(NULL),n)
            output["residual"]=take(double(NULL),n)
            if(n==0) return transpose(output)
            selected=table(long(0..(n-1)) as row_id,string(code) as code,timestamp(time) as time)
            if(type(on)!=VOID) selected=selected[normalize_on(on,n)]
            for(current_code in distinct(selected.code)) {
                rows=select row_id,time from selected where code=current_code order by time,row_id
                indices=rows.row_id
                fitted=rolling_controls_regression(target[indices],controls[indices],window,minimum,intercept)
                for(name in fitted.columnNames()) {
                    if(!(name in output)) output[name]=take(double(NULL),n)
                    values=output[name]
                    values[indices]=fitted[name]
                    output[name]=values
                }
            }
            return transpose(output)
        }
    ''')
    try:
        yield session
    finally:
        session.close()


def source():
    rng = np.random.default_rng(926)
    days = pd.bdate_range("2025-01-02", periods=42)
    stocks = 12
    x = rng.normal(size=len(days))
    z = rng.normal(size=len(days))
    return pd.DataFrame({
        "time": np.tile(days.to_numpy(), stocks),
        "code": np.repeat([f"S{i:02}" for i in range(stocks)], len(days)),
        "target": np.concatenate([0.2 + (i + 1) * x - 0.7 * z + rng.normal(0, 0.1, len(days)) for i in range(stocks)]),
        "x": np.tile(x, stocks), "z": np.tile(z, stocks),
        "category": np.tile(np.array(["a", "b", "c"])[np.arange(len(days)) // 7 % 3], stocks),
        "flag": np.tile(np.arange(len(days)) % 2 == 0, stocks),
        "constant": np.ones(stocks * len(days)),
        "selected": np.ones(stocks * len(days), dtype=bool),
    })


def compare(session, frame, controls, *, window=8, minimum=4, intercept=True, on="batchTestSource.selected"):
    session.upload({"batchTestSource": frame})
    selected = ",".join(f"batchTestSource.{name} as c{i}" for i, name in enumerate(controls))
    session.run(f"batchTestControls=table({selected});NULL")
    args = (f"batchTestSource.target,batchTestControls,{on},batchTestSource.code,batchTestSource.time,"
            f"{window},{minimum},{str(intercept).lower()}")
    legacy = session.run(f"batchTestLegacy({args})")
    actual = session.run(f"apply_rolling_ols({args},NULL)")
    assert set(legacy.columns) == set(actual.columns)
    names = sorted(legacy.columns)
    left = legacy.reindex(columns=names).to_numpy(dtype=float)
    right = actual.reindex(columns=names).to_numpy(dtype=float)
    np.testing.assert_array_equal(np.isnan(left), np.isnan(right))
    np.testing.assert_allclose(left, right, atol=1e-10, rtol=1e-7, equal_nan=True)
    return actual


def test_batch_helper_keeps_numeric_work_in_common():
    assert CONTROLS_REGRESSION_BATCH.module == "common"
    assert CONTROLS_REGRESSION_BATCH.parameters == ("targets", "controls", "intercept", "current_valid")
    assert ROLLING_CONTROLS_REGRESSION.parameters == ("target", "controls", "window", "min_periods", "intercept")
    for heading in ("Parameters", "Returns", "Notes"):
        assert heading in CONTROLS_REGRESSION_BATCH.definition


@pytest.mark.parametrize("intercept", [False, True])
@pytest.mark.parametrize("minimum", [1, 4, 8])
@pytest.mark.parametrize("controls", [
    ["x"], ["z", "x"], ["x", "category", "flag", "constant"],
    ["category"], ["flag"], ["constant"],
])
def test_batched_outputs_match_each_stock_window(dolphin, intercept, minimum, controls):
    compare(dolphin, source().sample(frac=1, random_state=4).reset_index(drop=True), controls,
            intercept=intercept, minimum=minimum)


@pytest.mark.parametrize("mode", ["shared", "individual", "mixed", "current_missing", "nonfinite"])
def test_each_target_and_control_validity_mask_is_preserved(dolphin, mode):
    frame = source()
    day = frame.groupby("code").cumcount()
    stock = frame.code.str[1:].astype(int)
    if mode == "shared":
        frame.loc[day.isin([7, 15]), "target"] = np.nan
    elif mode == "individual":
        frame.loc[(day + stock) % 11 == 0, "target"] = np.nan
        frame.loc[(day * 2 + stock) % 17 == 0, "x"] = np.nan
    elif mode == "mixed":
        frame.loc[(stock < 6) & (day % 13 == 0), "target"] = np.nan
        frame.loc[(stock >= 6) & (day % 9 == 0), "category"] = None
    elif mode == "current_missing":
        frame.loc[day == day.max(), "target"] = np.nan
    else:
        frame.loc[(day + stock) % 11 == 0, "target"] = np.inf
        frame.loc[(day * 2 + stock) % 17 == 0, "x"] = -np.inf
    actual = compare(dolphin, frame, ["x", "category"], minimum=3)
    if mode == "current_missing":
        rows = frame.index[day == day.max()]
        assert actual.loc[rows, "residual"].isna().all()
        assert actual.loc[rows, "alpha"].notna().all()


@pytest.mark.parametrize("mode", ["shared_gaps", "different_gaps", "absent_rows", "all_false", "scalar_true", "duplicate_times"])
def test_stock_specific_on_and_actual_window_dates_are_preserved(dolphin, mode):
    frame = source()
    day = frame.groupby("code").cumcount()
    stock = frame.code.str[1:].astype(int)
    if mode == "shared_gaps":
        frame.loc[day.isin([8, 9, 20]), "selected"] = False
    elif mode == "different_gaps":
        frame.loc[(day + stock) % 9 == 0, "selected"] = False
    elif mode == "absent_rows":
        frame = frame.loc[(day + stock) % 9 != 0].reset_index(drop=True)
    elif mode == "all_false":
        frame["selected"] = False
    elif mode == "duplicate_times":
        frame.loc[day == 12, "time"] = pd.Timestamp("2025-01-17")
    compare(dolphin, frame, ["x", "z"], on="true" if mode == "scalar_true" else "batchTestSource.selected")


@pytest.mark.parametrize("intercept", [False, True])
def test_collinearity_and_variable_active_columns_keep_minimum_norm_solution(dolphin, intercept):
    frame = source()
    frame["z"] = 2 * frame.x
    frame.loc[frame.time <= frame.time.unique()[9], "constant"] = frame.x
    compare(dolphin, frame, ["x", "z", "constant", "category"], intercept=intercept, minimum=1)


def test_nearly_equal_controls_are_not_merged(dolphin):
    frame = source()
    frame.loc[frame.code.eq("S01"), "x"] += 1e-14
    frame.loc[frame.code.eq("S02"), "z"] += 1e-12
    compare(dolphin, frame, ["x", "z"])


def test_batch_future_rows_do_not_change_current_category_index(dolphin):
    frame = source()
    full = compare(dolphin, frame, ["category", "x"], minimum=1)
    prefix = frame.loc[frame.time <= frame.time.unique()[21]].copy()
    truncated = compare(dolphin, prefix.reset_index(drop=True), ["category", "x"], minimum=1)
    names = sorted(set(full.columns) | set(truncated.columns))
    np.testing.assert_allclose(full.loc[prefix.index].reindex(columns=names), truncated.reindex(columns=names),
                               atol=1e-10, rtol=1e-7, equal_nan=True)


def test_batch_dispatch_keeps_nested_controls_and_shared_output_cache(dolphin):
    frame = source()
    common = {
        "type": "TS", "fields": {"target": "target", "controls": [
            {"type": "DIRECT", "op": "binary.add", "fields": {"left": "x", "right": 0.0}},
            {"type": "DIRECT", "op": "unary.cast", "fields": {"col": "category"}, "params": {"dtype": "symbol"}},
        ]},
        "params": {"window": 8, "min_periods": 4},
        "on": {"type": "DIRECT", "op": "binary.eq", "fields": {"left": "selected", "right": True}},
    }
    derivatives = {
        "alpha": {**common, "op": "controls.rolling_alpha"},
        "residual": {**common, "op": "controls.rolling_residual"},
        "beta0": {**common, "op": "controls.rolling_beta", "params": {**common["params"], "index": 0}},
    }
    request = FactorQuery.model_validate({
        "start_date": "2025-01-01", "end_date": "2025-12-31", "codes": ["S00"], "derivatives": derivatives,
    })
    parsed = {name: value.model_dump(mode="json") for name, value in request.derivatives.items()}
    dolphin.upload({"batchTestSource": frame, "batchTestDefinitions": json.dumps(parsed)})
    actual = dolphin.run("compute_factors(batchTestSource,fromStdJson(batchTestDefinitions))")
    reference = compare(dolphin, frame, ["x", "category"])
    for name in ("alpha", "beta0", "residual"):
        np.testing.assert_allclose(actual[name], reference[name], atol=1e-10, equal_nan=True)


@pytest.mark.parametrize("mode", ["empty", "all_missing", "one_stock", "individual_controls"])
def test_batch_boundaries_and_nonshared_fallback(dolphin, mode):
    frame = source()
    if mode == "empty":
        frame = frame.iloc[:0]
    elif mode == "all_missing":
        frame["target"] = np.nan
    elif mode == "one_stock":
        frame = frame.loc[frame.code.eq("S00")]
    else:
        frame["x"] += np.arange(len(frame)) * 0.0001
    compare(dolphin, frame, ["x", "z"])


@pytest.mark.parametrize("window,minimum", [(1, 1), (2, 1), (2, 2), (63, 1), (63, 42)])
def test_partial_and_single_observation_windows_keep_fallback(dolphin, window, minimum):
    compare(dolphin, source(), ["x", "category", "flag"], window=window, minimum=minimum)


def test_signature_hash_collisions_do_not_merge_different_windows(dolphin):
    from query.database.compile.query.functions.runtime import APPLY_ROLLING_OLS

    definition = APPLY_ROLLING_OLS.definition.replace(
        "def apply_rolling_ols(", "def batchTestCollisions("
    ).replace("msum(signature, int(window), 1) as key1", "take(long(0), size(signature)) as key1").replace(
        "msum(signature_hash, int(window), 1) as key2", "take(long(0), size(signature_hash)) as key2"
    )
    dolphin.run(definition)
    frame = source()
    day = frame.groupby("code").cumcount()
    stock = frame.code.str[1:].astype(int)
    frame.loc[(stock % 3 == 0) & (day % 7 == 0), "selected"] = False
    frame.loc[(stock % 3 == 1) & (day % 11 == 0), "selected"] = False
    dolphin.upload({"batchTestSource": frame})
    args = ("batchTestSource.target,table(batchTestSource.x as x),batchTestSource.selected,"
            "batchTestSource.code,batchTestSource.time,8,4,true")
    expected = dolphin.run(f"batchTestLegacy({args})")
    actual = dolphin.run(f"batchTestCollisions({args})")
    names = sorted(set(expected.columns) | set(actual.columns))
    np.testing.assert_allclose(expected.reindex(columns=names), actual.reindex(columns=names),
                               atol=1e-10, rtol=1e-7, equal_nan=True)


def test_batched_alpha_betas_residual_share_one_fit_cache(dolphin):
    frame = source()
    common = {"type": "TS", "fields": {"target": "target", "controls": ["x", "z"]},
              "params": {"window": 8, "min_periods": 4}}
    derivatives = {
        "alpha": {**common, "op": "controls.rolling_alpha"},
        "residual": {**common, "op": "controls.rolling_residual"},
        "beta0": {**common, "op": "controls.rolling_beta", "params": {**common["params"], "index": 0}},
        "beta1": {**common, "op": "controls.rolling_beta", "params": {**common["params"], "index": 1}},
    }
    request = FactorQuery.model_validate({"start_date": "2025-01-01", "end_date": "2025-12-31",
                                         "codes": ["S00"], "derivatives": derivatives})
    parsed = {name: node.model_dump(mode="json") for name, node in request.derivatives.items()}
    dolphin.upload({"batchTestSource": frame, "batchTestDefinitions": json.dumps(parsed)})
    keys = dolphin.run('''
        batchTestParsed=fromStdJson(batchTestDefinitions)
        batchTestCache=dict(STRING,ANY)
        batchTestStates=dict(STRING,INT)
        for(name in string(batchTestParsed.keys()))
            evaluate_definition(evaluate_node,batchTestSource,batchTestParsed,batchTestCache,batchTestStates,name)
        string(batchTestCache.keys())
    ''')
    assert sum(str(key).startswith("_query_rolling_ols_") for key in keys) == 1


def test_nullable_on_is_not_an_observation(dolphin):
    frame = source()
    dolphin.upload({"batchTestSource": frame})
    dolphin.run('''
        batchTestOn=batchTestSource.selected
        batchTestOn[2 44 86]=bool(NULL)
        batchTestSource["selected"]=batchTestOn
        batchTestControls=table(batchTestSource.x as x,batchTestSource.z as z)
        NULL
    ''')
    args = ("batchTestSource.target,batchTestControls,batchTestSource.selected,"
            "batchTestSource.code,batchTestSource.time,8,4,true")
    expected = dolphin.run(f"batchTestLegacy({args})")
    actual = dolphin.run(f"apply_rolling_ols({args},NULL)")
    names = sorted(set(expected.columns) | set(actual.columns))
    np.testing.assert_allclose(expected.reindex(columns=names), actual.reindex(columns=names),
                               atol=1e-10, rtol=1e-7, equal_nan=True)
    assert actual.loc[[2, 44, 86]].isna().all().all()


def test_non_numeric_target_still_raises(dolphin):
    frame = source()
    dolphin.upload({"batchTestSource": frame})
    args = ("batchTestSource.flag,table(batchTestSource.x as x),batchTestSource.selected,"
            "batchTestSource.code,batchTestSource.time,8,4,true")
    for function in ("batchTestLegacy", "apply_rolling_ols"):
        with pytest.raises(RuntimeError, match="target 必须是数值"):
            dolphin.run(f"{function}({args})")
