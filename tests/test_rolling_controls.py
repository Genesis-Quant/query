"""Continuous and categorical TS/CS regressions match independent NumPy fits."""

import json
import os

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from query import Derivative, FactorQuery, compile, create_session

TS_OPERATIONS = ["controls.rolling_alpha", "controls.rolling_beta", "controls.rolling_residual"]
CS_OPERATIONS = ["controls.alpha", "controls.beta", "controls.residual"]


def node(operation, *, controls=None, **params):
    rolling = operation in TS_OPERATIONS
    return {
        "type": "TS" if rolling else "CS",
        "op": operation,
        "fields": {"target": "target", "controls": ["x", "z"] if controls is None else controls},
        "params": {**({"window": 8, "fill": None} if rolling else {}), **params},
    }


def request(derivatives):
    return {
        "start_date": "2026-01-01", "end_date": "2026-03-31", "codes": ["A", "B"],
        "derivatives": derivatives,
    }


@pytest.mark.parametrize("operation", TS_OPERATIONS)
@pytest.mark.parametrize("params", [
    {"window": True}, {"window": 0}, {"min_periods": 9}, {"min_periods": 0},
    {"intercept": 1}, {"min_periods": False},
])
def test_invalid_rolling_parameters_are_rejected(operation, params):
    with pytest.raises(ValidationError):
        FactorQuery.model_validate(request({"result": node(operation, **params)}))


@pytest.mark.parametrize("operation", ["controls.beta", "controls.rolling_beta"])
@pytest.mark.parametrize("index", [-1, True, 1.5])
def test_beta_index_requires_nonnegative_integer(operation, index):
    with pytest.raises(ValidationError):
        FactorQuery.model_validate(request({"result": node(operation, index=index)}))


@pytest.mark.parametrize("operation", TS_OPERATIONS + CS_OPERATIONS)
def test_empty_controls_and_extra_parameters_are_rejected(operation):
    with pytest.raises(ValidationError):
        FactorQuery.model_validate(request({"result": node(operation, controls=[])}))
    with pytest.raises(ValidationError):
        FactorQuery.model_validate(request({"result": node(operation, residual_std=True)}))


@pytest.mark.parametrize("operation", ["controls.beta", "controls.rolling_beta"])
def test_beta_index_is_not_limited_to_unexpanded_control_count(operation):
    FactorQuery.model_validate(request({"result": node(operation, controls=["industry"], index=3)}))


def test_controls_regression_is_shared_from_common():
    from query.database.compile import collect_functions
    from query.database.compile.common.functions import (
        COMMON_FUNCTIONS,
        CONTROLS_REGRESSION,
        FILL_REGRESSION_INPUTS,
        ROLLING_CONTROLS_REGRESSION,
    )
    from query.database.compile.common.functions.numeric import (
        CONTROLS_REGRESSION as NUMERIC_CONTROLS_REGRESSION,
    )
    from query.database.compile.query.functions import cross_section, time_series

    assert CONTROLS_REGRESSION is NUMERIC_CONTROLS_REGRESSION
    assert CONTROLS_REGRESSION.module == "common"
    assert CONTROLS_REGRESSION in COMMON_FUNCTIONS
    for suffix in ("ALPHA", "BETA", "RESIDUAL"):
        assert getattr(cross_section, "CS_CONTROLS_" + suffix).dependencies == (CONTROLS_REGRESSION,)
    assert CONTROLS_REGRESSION in ROLLING_CONTROLS_REGRESSION.dependencies
    assert ROLLING_CONTROLS_REGRESSION.module == "common"
    assert ROLLING_CONTROLS_REGRESSION in COMMON_FUNCTIONS
    for suffix in ("ALPHA", "BETA", "RESIDUAL"):
        assert getattr(time_series, "TS_CONTROLS_ROLLING_" + suffix).dependencies == (
            ROLLING_CONTROLS_REGRESSION, FILL_REGRESSION_INPUTS,
        )
    assert collect_functions([CONTROLS_REGRESSION], "common")[-1] is CONTROLS_REGRESSION
    assert compile().count("def controls_regression(") == 1
    assert compile().count("def rolling_controls_regression(") == 1


def test_dos_operator_signatures_accept_raw_fields_and_parameters():
    from query.database.compile.query.functions import cross_section, time_series

    for suffix in ("ALPHA", "BETA", "RESIDUAL"):
        ts = getattr(time_series, "TS_CONTROLS_ROLLING_" + suffix)
        cs = getattr(cross_section, "CS_CONTROLS_" + suffix)
        index = ("index",) if suffix == "BETA" else ()
        assert ts.parameters == ("target", "controls", "window", "min_periods", "intercept") + index + ("fill",)
        assert cs.parameters == ("target", "controls", "intercept") + index
        for function in (ts, cs):
            for heading in ("Parameters", "Returns", "Notes", "Examples"):
                assert heading in function.definition


def test_registration_removes_old_name_and_keeps_binary_regressions():
    for operation in TS_OPERATIONS + CS_OPERATIONS:
        assert operation in Derivative.operators
    for operation in ("binary.rolling_alpha", "binary.rolling_beta", "binary.rolling_residual"):
        assert operation in Derivative.operators
    assert "controls.neutralize_by" not in Derivative.operators
    assert "cs_controls_neutralize_by" not in compile()
    with pytest.raises(ValidationError):
        FactorQuery.model_validate(request({"result": node("controls.neutralize_by")}))
    model = FactorQuery.model_validate(request(definitions()))
    assert model.source_factors() == ["target", "x", "z"]
    assert FactorQuery.model_validate_json(model.model_dump_json()) == model


@pytest.fixture(scope="module")
def dolphin():
    if os.getenv("QUERY_TEST_DOLPHINDB") != "1":
        pytest.skip("requires explicit opt-in to the configured DolphinDB server")
    session = create_session(max_time=300)
    try:
        yield session
    finally:
        session.close()


def data():
    rng = np.random.default_rng(71)
    rows = []
    for code in ("A", "B"):
        x = rng.normal(size=28)
        z = rng.normal(size=28)
        y = 0.7 + 1.4 * x - 0.8 * z + rng.normal(scale=0.2, size=28)
        for i, time in enumerate(pd.bdate_range("2026-01-05", periods=28)):
            rows.append({
                "time": time, "code": code, "target": y[i], "x": x[i], "z": z[i],
                "selected": i % 5 != 0, "industry": ("bank", "retail", "tech")[i % 3],
                "flag": i % 2 == 0, "constant": 1.0,
            })
    return pd.DataFrame(rows)


def cross_section_data():
    source = pd.concat([data()] * 4, ignore_index=True)
    source["time"] = np.repeat(pd.date_range("2026-01-05", periods=4), len(source) // 4)
    source["code"] = [f"C{index:03}" for index in range(len(source))]
    return source.sample(frac=1, random_state=10).reset_index(drop=True)


def evaluate(session, source, derivatives, *, cache=False, nullable_on=False):
    model = FactorQuery.model_validate(request(derivatives))
    parsed = {name: value.model_dump(mode="json") for name, value in model.derivatives.items()}
    session.upload({"regressionTestSource": source, "regressionTestDefinitions": json.dumps(parsed)})
    if nullable_on:
        session.run('regressionTestOn=regressionTestSource.selected; regressionTestOn[2]=bool(NULL); regressionTestSource["selected"]=regressionTestOn; NULL')
    if not cache:
        return session.run("compute_factors(regressionTestSource,fromStdJson(regressionTestDefinitions))")
    return session.run('''
        regressionTestCache=dict(STRING,ANY)
        regressionTestStates=dict(STRING,INT)
        regressionTestParsed=fromStdJson(regressionTestDefinitions)
        for (name in string(regressionTestParsed.keys()))
            evaluate_definition(evaluate_node,regressionTestSource,regressionTestParsed,regressionTestCache,regressionTestStates,name)
        string(regressionTestCache.keys())
    ''')


def fit(sample, controls, *, intercept=True):
    valid = np.isfinite(sample.target.to_numpy(dtype=float))
    categorical = []
    for name in controls:
        values = sample[name]
        category = not pd.api.types.is_numeric_dtype(values.dtype) or pd.api.types.is_bool_dtype(values.dtype)
        categorical.append(category)
        valid &= values.notna().to_numpy() if category else np.isfinite(values.to_numpy(dtype=float))
    residual = np.full(len(sample), np.nan)
    if not valid.any():
        return valid, np.nan, np.array([]), residual
    selected = sample.loc[valid]
    y = selected.target.to_numpy(dtype=float)
    encoded = []
    for name, category in zip(controls, categorical, strict=True):
        values = selected[name]
        if category:
            for level in sorted(values.unique())[1:]:
                encoded.append((values == level).to_numpy(dtype=float))
        else:
            encoded.append(values.to_numpy(dtype=float))
    beta = np.zeros(len(encoded))
    active = [i for i, values in enumerate(encoded) if len(np.unique(values)) > 1]
    alpha = y.mean()
    errors = y - alpha
    if active and len(y) > 1 and len(y) > len(active) + int(intercept):
        design = np.column_stack([encoded[i] for i in active])
        if intercept:
            design = np.column_stack([np.ones(len(y)), design])
        coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
        alpha = coefficients[0] if intercept else 0.0
        beta[active] = coefficients[int(intercept):]
        errors = y - design @ coefficients
    residual[valid] = errors
    return valid, alpha, beta, residual


def expected(source, *, controls=("x", "z"), window=8, minimum=8, intercept=True,
             on=False, cs=False, betas=2):
    columns = ["alpha", "residual", *[f"beta{i}" for i in range(betas)]]
    output = pd.DataFrame(np.nan, index=source.index, columns=columns)
    for _, group in source.groupby("time" if cs else "code", sort=False):
        if not cs:
            group = group.sort_values("time")
        if on:
            group = group.loc[group.selected.fillna(False)]
        windows = [group] if cs else [group.iloc[max(0, i - window + 1):i + 1] for i in range(len(group))]
        for sample in windows:
            valid, alpha, beta, residual = fit(sample, controls, intercept=intercept)
            if not cs and valid.sum() < minimum:
                continue
            positions = sample.index[valid] if cs else sample.index[-1:]
            output.loc[positions, "alpha"] = alpha
            output.loc[positions, "residual"] = residual[valid] if cs else residual[-1]
            for i in range(min(betas, len(beta))):
                output.loc[positions, f"beta{i}"] = beta[i]
    return output


def definitions(*, controls=None, cs=False, betas=2, **params):
    names = ("controls.alpha", "controls.beta", "controls.residual") if cs else TS_OPERATIONS
    result = {
        "alpha": node(names[0], controls=controls, **params),
        "residual": node(names[2], controls=controls, **params),
    }
    for index in range(betas):
        result[f"beta{index}"] = node(names[1], controls=controls, index=index, **params)
    return result


def assert_outputs(actual, reference):
    np.testing.assert_allclose(actual[reference.columns], reference, atol=1e-10, equal_nan=True)


@pytest.mark.parametrize("intercept", [False, True])
@pytest.mark.parametrize("minimum", [1, 4, 8])
def test_numeric_outputs_match_each_numpy_window(dolphin, intercept, minimum):
    source = data().sample(frac=1, random_state=9).reset_index(drop=True)
    actual = evaluate(dolphin, source, definitions(intercept=intercept, min_periods=minimum))
    assert_outputs(actual, expected(source, intercept=intercept, minimum=minimum))


@pytest.mark.parametrize("cs", [False, True])
@pytest.mark.parametrize("intercept", [False, True])
@pytest.mark.parametrize("controls", [
    ["industry"], ["flag"], ["industry", "x", "flag", "constant"], ["z", "x"],
])
def test_categorical_mixed_and_ordered_controls_match_numpy(dolphin, cs, intercept, controls):
    source = cross_section_data() if cs else data()
    params = {} if cs else {"min_periods": 2}
    actual = evaluate(dolphin, source, definitions(controls=controls, cs=cs, betas=6, intercept=intercept, **params))
    reference = expected(source, controls=controls, cs=cs, betas=6, intercept=intercept, minimum=2)
    assert_outputs(actual, reference)


@pytest.mark.parametrize("cs", [False, True])
def test_symbol_cast_is_categorical_and_matches_string(dolphin, cs):
    source = cross_section_data() if cs else data()
    params = {} if cs else {"min_periods": 2}
    derivatives = definitions(controls=["industry", "x"], cs=cs, betas=4, **params)
    derivatives["symbol_industry"] = {
        "type": "DIRECT", "op": "unary.cast", "fields": {"col": "industry"},
        "params": {"dtype": "symbol"},
    }
    for name, derivative in list(derivatives.items()):
        if name != "symbol_industry":
            derivatives["symbol_" + name] = {
                **derivative, "fields": {"target": "target", "controls": ["symbol_industry", "x"]},
            }
    actual = evaluate(dolphin, source, derivatives)
    for name in ("alpha", "residual", "beta0", "beta1", "beta2", "beta3"):
        np.testing.assert_allclose(actual[name], actual["symbol_" + name], atol=1e-10, equal_nan=True)


@pytest.mark.parametrize("cs", [False, True])
def test_common_missing_mask_and_nonfinite_values(dolphin, cs):
    source = cross_section_data() if cs else data()
    source.loc[3, "target"] = np.nan
    source.loc[4, "x"] = np.nan
    source.loc[5, "industry"] = None
    source.loc[12, "x"] = np.inf
    source.loc[18, "target"] = -np.inf
    controls = ["industry", "x", "flag"]
    params = {} if cs else {"min_periods": 2}
    actual = evaluate(dolphin, source, definitions(controls=controls, cs=cs, betas=5, **params))
    assert_outputs(actual, expected(source, controls=controls, cs=cs, betas=5, minimum=2))
    assert actual.loc[[3, 4, 5, 12, 18], "residual"].isna().all()


@pytest.mark.parametrize("cs", [False, True])
def test_on_filters_groups_and_restores_original_rows(dolphin, cs):
    source = cross_section_data() if cs else data()
    source.loc[2, "selected"] = False
    params = {} if cs else {"min_periods": 2}
    derivatives = definitions(controls=["industry", "x"], cs=cs, betas=4, **params)
    for value in derivatives.values():
        value["on"] = {"type": "DIRECT", "op": "binary.eq", "fields": {"left": "selected", "right": True}}
    actual = evaluate(dolphin, source, derivatives, nullable_on=True)
    assert_outputs(actual, expected(source, controls=["industry", "x"], cs=cs, betas=4, minimum=2, on=True))
    for value in derivatives.values():
        value["on"] = False
    masked = evaluate(dolphin, source, derivatives)
    assert masked[["alpha", "residual", "beta0", "beta1", "beta2", "beta3"]].isna().all().all()


@pytest.mark.parametrize("cs", [False, True])
@pytest.mark.parametrize("controls", [["constant"], ["industry"], ["x", "z"]])
@pytest.mark.parametrize("intercept", [False, True])
def test_constants_and_insufficient_samples_follow_demean_fallback(dolphin, cs, controls, intercept):
    source = data().iloc[:2].copy()
    source["industry"] = "only"
    if cs:
        source["time"] = source.time.iloc[0]
    params = {} if cs else {"min_periods": 1}
    actual = evaluate(dolphin, source, definitions(controls=controls, cs=cs, betas=4, intercept=intercept, **params))
    assert_outputs(actual, expected(source, controls=controls, cs=cs, betas=4, intercept=intercept, minimum=1))


def test_singular_controls_match_svd_minimum_norm_solution(dolphin):
    source = data()
    source["z"] = 2 * source.x
    actual = evaluate(dolphin, source, definitions())
    assert_outputs(actual, expected(source))


def test_categories_are_recomputed_without_looking_at_future_rows(dolphin):
    source = data().iloc[:28].copy()
    source["industry"] = ["bank"] * 5 + ["retail"] * 5 + ["tech"] * 9 + ["z_future"] * 9
    derivatives = definitions(controls=["industry", "x"], betas=5, min_periods=2)
    actual = evaluate(dolphin, source, derivatives)
    assert_outputs(actual, expected(source, controls=["industry", "x"], betas=5, minimum=2))
    truncated = evaluate(dolphin, source.iloc[:19], derivatives)
    np.testing.assert_allclose(actual.loc[:18, ["alpha", "residual", "beta0", "beta1", "beta2", "beta3", "beta4"]],
                               truncated[["alpha", "residual", "beta0", "beta1", "beta2", "beta3", "beta4"]], atol=1e-10, equal_nan=True)


def test_one_control_matches_existing_binary_regression(dolphin):
    derivatives = definitions(controls=["x"], betas=1)
    for suffix in ("alpha", "beta", "residual"):
        derivatives["old_" + suffix] = {
            "type": "TS", "op": "binary.rolling_" + suffix,
            "fields": {"left": "x", "right": "target"}, "params": {"window": 8},
        }
    actual = evaluate(dolphin, data(), derivatives)
    for name, old in (("alpha", "old_alpha"), ("beta0", "old_beta"), ("residual", "old_residual")):
        np.testing.assert_allclose(actual[name], actual[old], atol=1e-10, equal_nan=True)


def test_shared_fit_cache_is_one_entry_for_all_outputs(dolphin):
    keys = evaluate(dolphin, data(), definitions(), cache=True)
    assert sum(str(key).startswith("_query_rolling_ols_") for key in keys) == 1
    derivatives = definitions()
    derivatives["different"] = node("controls.rolling_beta", window=9)
    keys = evaluate(dolphin, data(), derivatives, cache=True)
    assert sum(str(key).startswith("_query_rolling_ols_") for key in keys) == 2
    derivatives = definitions()
    derivatives["different"] = {
        **node("controls.rolling_alpha"),
        "on": {"type": "DIRECT", "op": "binary.eq", "fields": {"left": "selected", "right": True}},
    }
    keys = evaluate(dolphin, data(), derivatives, cache=True)
    assert sum(str(key).startswith("_query_rolling_ols_") for key in keys) == 2


def test_internal_cache_does_not_override_user_named_factor(dolphin):
    keys = evaluate(dolphin, data(), definitions(), cache=True)
    reserved = next(str(key) for key in keys if str(key).startswith("_query_rolling_ols_"))
    derivatives = definitions()
    derivatives[reserved] = {"type": "DIRECT", "op": "binary.add", "fields": {"left": "x", "right": 1}}
    actual = evaluate(dolphin, data(), derivatives)
    assert_outputs(actual, expected(data()))
    np.testing.assert_allclose(actual[reserved], data().x + 1)


def test_daily_residual_then_volatility_preserves_warmup_nulls(dolphin):
    source = data()
    derivatives = definitions()
    derivatives["volatility"] = {
        "type": "TS", "op": "unary.rolling_std", "fields": {"col": "residual"},
        "params": {"window": 5, "min_periods": 5},
    }
    actual = evaluate(dolphin, source, derivatives)
    residual = expected(source).residual
    volatility = residual.groupby(source.code, sort=False).transform(lambda values: values.rolling(5, min_periods=5).std())
    np.testing.assert_allclose(actual.residual, residual, atol=1e-10, equal_nan=True)
    np.testing.assert_allclose(actual.volatility, volatility, atol=1e-10, equal_nan=True)


@pytest.mark.parametrize("cs", [False, True])
@pytest.mark.parametrize("intercept", [False, True])
def test_direct_dos_functions_match_dsl_outputs(dolphin, cs, intercept):
    source = data().iloc[:28].copy()
    if cs:
        source["time"] = source.time.iloc[0]
    params = {} if cs else {"min_periods": 2}
    actual = evaluate(dolphin, source, definitions(controls=["industry", "x"], cs=cs, betas=4, intercept=intercept, **params))
    dolphin.run('regressionTestControls=table(regressionTestSource.industry as industry,regressionTestSource.x as x); NULL')
    literal = "true" if intercept else "false"
    prefix = "cs_controls_" if cs else "ts_controls_rolling_"
    args = f'regressionTestSource.target,regressionTestControls,{"" if cs else "8,2,"}{literal}'
    for suffix, name, extra in [("alpha", "alpha", ""), ("residual", "residual", ""),
                                *[("beta", f"beta{i}", f",{i}") for i in range(4)]]:
        direct = dolphin.run(f'{prefix}{suffix}({args}{extra}{"" if cs else ",NULL"})')
        np.testing.assert_allclose(direct, actual[name], atol=1e-10, equal_nan=True)
    with pytest.raises(RuntimeError, match="index"):
        dolphin.run(f'{prefix}beta({args},-1)')


@pytest.mark.parametrize("cs", [False, True])
@pytest.mark.parametrize("empty", [False, True])
def test_empty_and_all_missing_sources_return_scalar_null_columns(dolphin, cs, empty):
    source = data().iloc[:0 if empty else 8].copy()
    source["target"] = np.nan
    actual = evaluate(dolphin, source, definitions(cs=cs, betas=4))
    columns = ["alpha", "residual", "beta0", "beta1", "beta2", "beta3"]
    assert len(actual) == len(source)
    assert actual[columns].isna().all().all()
