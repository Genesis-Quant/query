"""Opt-in numeric regressions against an isolated DolphinDB session.

Run with QUERY_TEST_DOLPHINDB=1. No DFS tables or installed modules are changed.
"""

import json
import os

import numpy as np
import pytest

from query.database import create_session


@pytest.fixture(scope="module")
def dolphin():
    if os.getenv("QUERY_TEST_DOLPHINDB") != "1":
        pytest.skip("requires explicit opt-in to the configured DolphinDB server")
    session = create_session(max_time=180)
    try:
        # create_session preloads the locally compiled functions.
        yield session
    finally:
        session.close()


@pytest.mark.parametrize("values", [
    [11.43, 10.13], [2, 3, 5, 7, 11, 13], [2, 2, 2],
    [1, np.nan, 3], [np.nan, np.nan], [7],
])
@pytest.mark.parametrize("ddof", [0, 1])
def test_cross_section_variance_matches_numpy_and_std(dolphin, values, ddof):
    values = np.asarray(values, dtype=float)
    valid = values[np.isfinite(values)]
    expected = float(np.var(valid, ddof=ddof)) if len(valid) > ddof else np.nan
    dolphin.upload({"auditValues": values, "auditDdof": ddof})
    actual = dolphin.run("cs_unary_var(auditValues,auditDdof)")
    standard_deviation = dolphin.run("cs_unary_std(auditValues,auditDdof)")
    assert actual.shape == values.shape
    np.testing.assert_allclose(actual, expected, equal_nan=True)
    np.testing.assert_allclose(actual, standard_deviation ** 2, equal_nan=True)


@pytest.mark.parametrize("left,right,expected", [
    ([0, 0], [1, 2], np.nan), ([1, 1], [2, 3], np.nan),
    ([1, np.nan], [2, 3], np.nan), ([np.nan, np.nan], [2, 3], np.nan),
    ([1], [2], np.nan), ([1, 2, 3], [3, 5, 7], 2),
    ([1, np.nan, 3], [3, 5, 7], 2),
])
def test_beta_handles_degenerate_and_paired_observations(dolphin, left, right, expected):
    dolphin.upload({"auditX": np.asarray(left, dtype=float), "auditY": np.asarray(right, dtype=float)})
    actual = dolphin.run("cs_binary_beta(auditX,auditY)")
    assert actual.shape == (len(left),)
    np.testing.assert_allclose(actual, expected, equal_nan=True)


@pytest.mark.parametrize("right,expected", [
    (0, [np.nan, np.nan, np.nan]),
    ("double(NULL)", [np.nan, np.nan, np.nan]),
    ("0.0 0.0 0.0", [np.nan, np.nan, np.nan]),
    ("0.0 2.0 NULL", [np.nan, 1, np.nan]),
    (2, [0.5, 1, 1.5]),
])
def test_division_preserves_shape_with_scalar_or_vector_denominators(dolphin, right, expected):
    actual = dolphin.run(f"direct_binary_div(1.0 2.0 3.0,{right})")
    assert actual.shape == (3,)
    np.testing.assert_allclose(actual, expected, equal_nan=True)


@pytest.mark.parametrize("function,parameters", [
    ("bars_since", ""), ("consecutive_count", ""),
    ("rolling_true_count", ",2,1"), ("rolling_all", ",2,1"), ("rolling_any", ",2,1"),
])
def test_condition_kernels_reject_numbers(dolphin, function, parameters):
    with pytest.raises(RuntimeError, match="必须是 BOOL"):
        dolphin.run(f"ts_unary_{function}(11.0 12.0{parameters})")


@pytest.mark.parametrize("definition", [
    {"type": "CS", "op": "binary.beta", "fields": {"left": "x", "right": "y"}, "params": {}, "on": False},
    {"type": "CS", "op": "binary.beta", "fields": {"left": "x", "right": "y"}, "params": {}},
    {"type": "DIRECT", "op": "binary.div", "fields": {"left": "x", "right": 0}, "params": {}},
])
def test_null_results_survive_full_dsl_evaluation(dolphin, definition):
    dolphin.upload({"auditDefinitions": json.dumps({"result": definition})})
    result = dolphin.run("""
        auditSource=table(take(timestamp(2025.01.02),2) as time,
            `000001.SZ`600000.SH as code, 1.0 1.0 as x, 2.0 3.0 as y)
        compute_factors(auditSource,fromStdJson(auditDefinitions))
    """)
    assert len(result) == 2
    assert result["result"].isna().all()


def test_variance_is_one_value_per_date_in_full_dsl(dolphin):
    dolphin.upload({"auditDefinitions": json.dumps({"variance": {
        "type": "CS", "op": "unary.var", "fields": {"col": "close"}, "params": {"ddof": 1},
    }})})
    result = dolphin.run("""
        auditSource=table(timestamp(2025.01.02 2025.01.02 2025.01.03 2025.01.03) as time,
            take(`000001.SZ`600000.SH,4) as code, 11.43 10.13 1.0 3.0 as close)
        compute_factors(auditSource,fromStdJson(auditDefinitions))
    """)
    np.testing.assert_allclose(result["variance"], [.845, .845, 2, 2])


@pytest.mark.parametrize("operation", ["atr", "natr"])
@pytest.mark.parametrize("period", [2, 14])
def test_atr_valid_periods_match_constant_true_range(dolphin, operation, period):
    close = np.arange(10, 40, dtype=float)
    dolphin.upload({"auditClose": close})
    result = dolphin.run(f"ts_talib_{operation}(auditClose+1,auditClose-1,auditClose,{period})")
    assert np.isnan(result[:period]).all()
    expected = np.full(len(close) - period, 2.0)
    if operation == "natr":
        expected = expected / close[period:] * 100
    np.testing.assert_allclose(result[period:], expected)
