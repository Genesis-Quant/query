"""Fixed-code factors keep the requested panel and the base field's fill rules."""

import os

import numpy as np
import pandas as pd
import pytest

from query import Derivative, DolphinSettings, FactorQuery, compile, create_session, execute_query
from query.apps.query.api import query_parameters
from query.database.compile.query.scripts import QUERY_SCRIPT
from query.workers import industry, stock_financial

CODES = ["600000.SH", "000001.SZ", "000002.SZ"]
INDEX = "000852.SH"
STOCK = "600036.SH"
WEIGHT = "weight_000300SH"
DATES = pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09", "2026-01-12"])
SETTINGS = DolphinSettings(username="test", password="unused")


def frame(rows):
    result = pd.DataFrame(rows, columns=["time", "code", "factor", "value"])
    result["time"] = pd.to_datetime(result["time"]).astype("datetime64[ms]")
    result["value"] = result["value"].astype(float)
    return result


def source():
    rows = []
    for day, time in enumerate(DATES):
        for position, code in enumerate(CODES):
            rows.append((time, code, "close", 10.0 * (position + 1) + day))
        for factor, values in {
            "close": [100, 102, 101, np.nan, 104, 108],
            "pct_chg": [1, 2, -1, np.nan, np.nan, 4],
            "custom_feature": [0, -2.5, 9, 3, 7, 4],
        }.items():
            rows.append((time, INDEX, factor, values[day]))
        rows.append((time, "000300.SH", "close", 200 + day))
        rows.append((time, STOCK, "close", 50 + day))
    rows.extend([
        ("2026-01-04", STOCK, "industry_l0", 1),
        ("2026-01-07", STOCK, "industry_l0", 2),
        ("2026-01-10", STOCK, "industry_l0", 3),
        ("2026-01-13", STOCK, "industry_l0", 4),
        ("2026-01-04", STOCK, "q_sales_yoy", 20),
        ("2026-01-06", STOCK, "q_sales_yoy", 30),
        ("2026-01-10", STOCK, "q_sales_yoy", 40),
        ("2026-01-13", STOCK, "q_sales_yoy", 50),
        ("2026-01-07", STOCK, "is_st", 1),
        ("2026-01-09", STOCK, "is_st", np.nan),
        ("2026-01-04", STOCK, WEIGHT, 0.2),
        ("2026-01-04", "OTHER", WEIGHT, 0.8),
        ("2026-01-07", "OTHER", WEIGHT, 1),
        ("2026-01-10", STOCK, WEIGHT, 0.4),
        ("2026-01-10", "OTHER", WEIGHT, 0.6),
        ("2026-01-13", "OTHER", WEIGHT, 1),
    ])
    return frame(rows)


def configuration(*, factors=None, derivatives=None, codes=None, start="2026-01-05", end="2026-01-12", **overrides):
    return dict(start_date=start, end_date=end, codes=CODES if codes is None else codes,
                factors=[] if factors is None else factors,
                derivatives={} if derivatives is None else derivatives, **overrides)


def direct(op, **fields):
    return {"type": "DIRECT", "op": op, "fields": fields}


def ts(op, col, **params):
    return {"type": "TS", "op": op, "fields": {"col": col}, "params": params}


def test_reference_strings_use_existing_schema_and_dependency_discovery():
    request = FactorQuery.model_validate(configuration(derivatives={
        "index_return": direct("binary.div", left="pct_chg@000852.SH", right=100.0),
        "excess": direct("binary.sub", left=ts("unary.pct_change", "close"), right="index_return"),
    }))
    assert request.source_factors() == ["close", "pct_chg@000852.SH"]
    parameters = query_parameters(request, SETTINGS)
    assert parameters["factors"].tolist() == ["close", "pct_chg@000852.SH"]
    assert parameters["codes"].tolist() == CODES
    assert parameters["columns"].tolist() == ["time", "code", "index_return", "excess"]
    assert FactorQuery.model_validate_json(request.model_dump_json()) == request
    assert "factor@code" in compile()
    assert len(Derivative.operators) == 231


def test_source_builders_have_no_initial_value_parameters_or_pre_start_reads():
    from query.database.compile.query.functions.runtime import (
        BUILD_DEFAULT_FACTOR_SOURCE,
        BUILD_FACTOR_SOURCE,
        BUILD_FIXED_CODE_FACTOR_SOURCE,
    )

    assert BUILD_FACTOR_SOURCE.parameters == (
        "data", "codes", "factors", "dates", "start_time", "end_time"
    )
    for function in (BUILD_FACTOR_SOURCE, BUILD_DEFAULT_FACTOR_SOURCE, BUILD_FIXED_CODE_FACTOR_SOURCE):
        assert not any("seed" in name for name in function.parameters)
        assert "time < start_time" not in function.definition
    assert "time < request.start" not in QUERY_SCRIPT


def test_compiler_uses_existing_worker_fill_classifications():
    import json
    from pathlib import Path

    script = compile()
    assert "financial_factors = " + json.dumps(sorted(stock_financial.FINANCIAL_FACTORS)) in script
    assert "industry_factors = " + json.dumps(list(industry.INDUSTRY_FACTORS)) in script
    assert "__FINANCIAL_FACTORS__" not in script
    assert "__INDUSTRY_FACTORS__" not in script
    assert not Path(industry.__file__).parents[1].joinpath("catalog.py").exists()


@pytest.fixture(scope="module")
def dolphin():
    if os.getenv("QUERY_TEST_DOLPHINDB") != "1":
        pytest.skip("requires explicit opt-in to the configured DolphinDB server")
    session = create_session(max_time=300)
    try:
        script = QUERY_SCRIPT.replace("def buildQuery(request)", "def referenceTestQuery(request)")
        script = script.replace("sourceTable = loadTable(request.database, request.table)", "sourceTable = request.source")
        session.run(script)
        yield session
    finally:
        session.close()


def evaluate(session, request, data=None):
    parameters = query_parameters(request, SETTINGS)
    session.upload({"referenceTestData": source() if data is None else data,
                    "referenceTestRequest": parameters})
    session.run('referenceTestRequest["source"] = referenceTestData; referenceTestResult = referenceTestQuery(referenceTestRequest); NULL')
    return session.run("referenceTestResult.data")


def builder(session, factors, data=None, *, dates=DATES, function="build_factor_source"):
    session.upload({"referenceTestData": source() if data is None else data,
                    "referenceTestFactors": np.asarray(factors, dtype=str),
                    "referenceTestCodes": np.asarray(CODES, dtype=str),
                    "referenceTestDates": pd.DatetimeIndex(dates).to_numpy(dtype="datetime64[ms]")})
    return session.run(f'{function}(referenceTestData, referenceTestCodes, referenceTestFactors, referenceTestDates, timestamp(2026.01.05), timestamp(2026.01.13))')


def series(result, column, code=CODES[0]):
    return result.loc[result.code == code].sort_values("time")[column].to_numpy()


def test_mixed_factors_preserve_rows_order_and_code_domain(dolphin):
    baseline = evaluate(dolphin, configuration(factors=["close"]))
    actual = evaluate(dolphin, configuration(factors=["close", f"close@{INDEX}", "close@000300.SH"]))
    pd.testing.assert_frame_equal(actual[["time", "code", "close"]], baseline)
    assert len(actual) == len(DATES) * len(CODES)
    assert set(actual.code) == set(CODES)
    for code in CODES:
        np.testing.assert_allclose(series(actual, f"close@{INDEX}", code), [100, 102, 101, np.nan, 104, 108], equal_nan=True)
        np.testing.assert_allclose(series(actual, "close@000300.SH", code), np.arange(200, 206))


def test_only_references_still_construct_full_requested_panel(dolphin):
    result = evaluate(dolphin, configuration(factors=[f"custom_feature@{INDEX}"]))
    assert list(result.columns) == ["time", "code", f"custom_feature@{INDEX}"]
    assert len(result) == len(CODES) * len(DATES)
    for code in CODES:
        np.testing.assert_allclose(series(result, f"custom_feature@{INDEX}", code), [0, -2.5, 9, 3, 7, 4])


def test_fixed_code_can_also_be_one_of_the_requested_stocks(dolphin):
    result = evaluate(dolphin, configuration(factors=[f"close@{CODES[0]}"]))
    for code in CODES:
        np.testing.assert_allclose(series(result, f"close@{CODES[0]}", code), np.arange(10, 16))


@pytest.mark.parametrize("reference", ["missing@000852.SH", "close@UNKNOWN"])
def test_absent_factor_or_code_is_null_not_zero(dolphin, reference):
    result = evaluate(dolphin, configuration(factors=[reference]))
    assert len(result) == len(CODES) * len(DATES)
    assert result[reference].isna().all()


def test_default_branch_remains_identical_to_original_source_builder(dolphin):
    for factors in ([], ["close"], ["close", "missing"]):
        actual = builder(dolphin, factors)
        expected = builder(dolphin, factors, function="build_default_factor_source")
        pd.testing.assert_frame_equal(actual, expected)


@pytest.mark.parametrize("reference", ["close@", "@000852.SH", "close@@000852.SH", "close@000852.SH@extra", "close @000852.SH", "close@ 000852.SH"])
def test_malformed_fixed_references_are_rejected(dolphin, reference):
    with pytest.raises(RuntimeError, match="factor@code"):
        builder(dolphin, [reference])


def test_duplicate_reference_names_and_daily_source_values_are_rejected(dolphin):
    with pytest.raises(RuntimeError, match="factors 不能重复"):
        builder(dolphin, [f"close@{INDEX}", f"close@{INDEX}"])
    data = source()
    duplicate = data.loc[(data.code == INDEX) & (data.factor == "close")].iloc[[0]].copy()
    duplicate["time"] = np.asarray(["2026-01-05T12:00:00"], dtype="datetime64[ms]")
    with pytest.raises(RuntimeError, match="每个日期只能有一条记录"):
        builder(dolphin, [f"close@{INDEX}"], pd.concat([data, duplicate], ignore_index=True))


def test_empty_date_axis_preserves_requested_reference_columns(dolphin):
    result = builder(dolphin, ["close", f"close@{INDEX}"], dates=[])
    assert result.empty
    assert list(result.columns) == ["time", "code", "selected", "close", f"close@{INDEX}"]


def test_st_default_fill_is_zero_without_forward_filling(dolphin):
    result = evaluate(dolphin, configuration(factors=[f"is_st@{STOCK}"]))
    np.testing.assert_allclose(series(result, f"is_st@{STOCK}"), [0, 0, 1, 0, 0, 0])


def test_financial_events_forward_fill_only_from_loaded_range(dolphin):
    result = evaluate(dolphin, configuration(factors=[f"q_sales_yoy@{STOCK}"]))
    np.testing.assert_allclose(series(result, f"q_sales_yoy@{STOCK}"), [np.nan, 30, 30, 30, 30, 40], equal_nan=True)
    expanded = evaluate(dolphin, configuration(factors=[f"q_sales_yoy@{STOCK}"], lookback="P2D"))
    np.testing.assert_allclose(series(expanded, f"q_sales_yoy@{STOCK}"), [20, 30, 30, 30, 30, 40])


def test_industry_head_stays_null_until_first_in_range_event(dolphin):
    result = evaluate(dolphin, configuration(factors=[f"industry_l0@{STOCK}"]))
    np.testing.assert_allclose(series(result, f"industry_l0@{STOCK}"), [np.nan, np.nan, 2, 2, 2, 3], equal_nan=True)


@pytest.mark.parametrize("factor", ["close", "pct_chg", "is_st", "industry_l0", "q_sales_yoy", WEIGHT])
def test_reference_fill_matches_same_field_on_its_own_security(dolphin, factor):
    target = INDEX if factor in {"close", "pct_chg"} else STOCK
    reference = f"{factor}@{target}"
    ordinary = evaluate(dolphin, configuration(factors=[factor], codes=[target]))
    broadcast = evaluate(dolphin, configuration(factors=[reference]))
    expected = ordinary.sort_values("time")[factor].to_numpy()
    for code in CODES:
        np.testing.assert_allclose(series(broadcast, reference, code), expected, equal_nan=True)


def test_weight_uses_only_in_range_snapshots_and_keeps_head_null(dolphin):
    reference = f"{WEIGHT}@{STOCK}"
    result = evaluate(dolphin, configuration(factors=[reference]))
    np.testing.assert_allclose(series(result, reference), [np.nan, np.nan, 0, 0, 0, 0.4], equal_nan=True)
    missing_member = evaluate(dolphin, configuration(factors=[f"{WEIGHT}@UNKNOWN"]))
    np.testing.assert_allclose(series(missing_member, f"{WEIGHT}@UNKNOWN"), [np.nan, np.nan, 0, 0, 0, 0], equal_nan=True)
    no_snapshot = evaluate(dolphin, configuration(factors=[f"weight_missing@{STOCK}"]))
    assert no_snapshot[f"weight_missing@{STOCK}"].isna().all()


def test_weight_stays_null_until_first_snapshot_when_no_prior_snapshot_exists(dolphin):
    data = source()
    data = data.loc[~((data.factor == WEIGHT) & (data.time < pd.Timestamp("2026-01-05")))].copy()
    result = evaluate(dolphin, configuration(factors=[f"{WEIGHT}@{STOCK}"]), data)
    np.testing.assert_allclose(series(result, f"{WEIGHT}@{STOCK}"), [np.nan, np.nan, 0, 0, 0, 0.4], equal_nan=True)


def test_nested_dsl_uses_index_return_and_does_not_output_dependencies(dolphin):
    result = evaluate(dolphin, configuration(derivatives={
        "index_return": direct("binary.div", left=f"pct_chg@{INDEX}", right=100.0),
        "excess": direct("binary.sub", left=ts("unary.pct_change", "close"), right="index_return"),
    }))
    assert list(result.columns) == ["time", "code", "index_return", "excess"]
    expected_index = np.asarray([0.01, 0.02, -0.01, np.nan, np.nan, 0.04])
    for position, code in enumerate(CODES):
        np.testing.assert_allclose(series(result, "index_return", code), expected_index, equal_nan=True)
        prices = pd.Series(10 * (position + 1) + np.arange(len(DATES)), dtype=float)
        expected = prices.pct_change(fill_method=None).to_numpy() - expected_index
        np.testing.assert_allclose(series(result, "excess", code), expected, equal_nan=True)


def test_ts_rolling_and_cs_ranks_do_not_include_external_security(dolphin):
    result = evaluate(dolphin, configuration(derivatives={
        "window": ts("unary.rolling_mean", f"close@{INDEX}", window=2, min_periods=2),
        "rank": {"type": "CS", "op": "unary.rank_pct", "fields": {
            "col": direct("binary.sub", left="close", right=f"close@{INDEX}")
        }, "params": {"ascending": True, "ties_method": "average"}},
    }))
    for position, code in enumerate(CODES):
        np.testing.assert_allclose(series(result, "window", code), [np.nan, 101, 101.5, np.nan, np.nan, 106], equal_nan=True)
        np.testing.assert_allclose(series(result, "rank", code), [(position + 1) / 3] * 3 + [np.nan] + [(position + 1) / 3] * 2, equal_nan=True)


def test_reference_bool_comparisons_work_in_on_and_filters(dolphin):
    result = evaluate(dolphin, configuration(derivatives={
        "valid": direct("binary.gt", left=f"pct_chg@{INDEX}", right=0),
        "rank": {"type": "CS", "op": "unary.rank_pct", "fields": {"col": "close"}, "on": "valid"},
    }, filters=["valid"]))
    assert sorted(pd.DatetimeIndex(result.time).unique()) == DATES[[0, 1, 5]].tolist()
    assert len(result) == 9
    for position, code in enumerate(CODES):
        np.testing.assert_allclose(series(result, "rank", code), [(position + 1) / 3] * 3)


def test_lookback_lookforward_and_missing_reference_dates_respect_original_output(dolphin):
    zero = evaluate(dolphin, configuration(start="2026-01-09", end="2026-01-09", derivatives={
        "next_index_close": ts("unary.shift", f"close@{INDEX}", periods=-1),
    }))
    assert zero.next_index_close.isna().all()
    future = evaluate(dolphin, configuration(start="2026-01-09", end="2026-01-09", lookforward="P3D", derivatives={
        "next_index_close": ts("unary.shift", f"close@{INDEX}", periods=-1),
    }))
    assert len(future) == len(CODES)
    assert future.time.eq(pd.Timestamp("2026-01-09")).all()
    assert future.next_index_close.eq(108).all()
    warm = evaluate(dolphin, configuration(start="2026-01-06", end="2026-01-06", lookback="P1D", derivatives={
        "index_return": ts("unary.pct_change", f"close@{INDEX}", periods=1),
    }))
    np.testing.assert_allclose(warm.index_return, 0.02)
    missing = evaluate(dolphin, configuration(start="2026-01-07", end="2026-01-07", lookforward="P2D", derivatives={
        "next_index_close": ts("unary.shift", f"close@{INDEX}", periods=-1),
    }))
    assert missing.next_index_close.isna().all()


def test_reference_events_never_add_rows_to_the_default_source_timeline(dolphin):
    factors = ["industry_l0", "q_sales_yoy"]
    data = source()
    extra = frame([
        ("2026-01-02", CODES[0], "industry_l0", 7),
        ("2026-01-06", CODES[1], "industry_l0", 8),
        ("2026-01-10", CODES[2], "q_sales_yoy", 9),
    ])
    data = pd.concat([data, extra], ignore_index=True)
    baseline = builder(dolphin, factors, data)
    actual = builder(dolphin, factors + [f"industry_l0@{STOCK}", f"q_sales_yoy@{STOCK}"], data)
    pd.testing.assert_frame_equal(actual[list(baseline.columns)], baseline)
    assert len(actual) == len(baseline)
    assert set(actual.code) == set(CODES)


def test_shuffled_source_rows_do_not_change_fixed_code_values(dolphin):
    request = configuration(factors=[f"close@{INDEX}", f"industry_l0@{STOCK}", f"{WEIGHT}@{STOCK}"])
    expected = evaluate(dolphin, request)
    actual = evaluate(dolphin, request, source().sample(frac=1, random_state=91).reset_index(drop=True))
    pd.testing.assert_frame_equal(actual, expected)


def test_missing_daily_records_do_not_skip_dates_for_ts_references(dolphin):
    data = source()
    data = data.loc[~((data.code == INDEX) & (data.factor == "close") & (data.time == pd.Timestamp("2026-01-08")))].copy()
    result = evaluate(dolphin, configuration(derivatives={
        "previous_close": ts("unary.shift", f"close@{INDEX}", periods=1),
    }), data)
    for code in CODES:
        np.testing.assert_allclose(series(result, "previous_close", code), [np.nan, 100, 102, 101, np.nan, 104], equal_nan=True)


@pytest.mark.parametrize("factor", ["industry_l0", "q_sales_yoy", WEIGHT])
@pytest.mark.parametrize("fixed", [False, True])
def test_pre_start_records_never_supply_initial_values(dolphin, factor, fixed):
    reference = f"{factor}@{STOCK}" if fixed else factor
    codes = CODES if fixed else [STOCK]
    request = configuration(factors=[reference], codes=codes)
    data = source()
    expected = evaluate(dolphin, request, data.loc[data.time >= DATES[0]].copy())
    actual = evaluate(dolphin, request, data)
    pd.testing.assert_frame_equal(actual, expected)
    assert actual.loc[actual.time == DATES[0], reference].isna().all()



@pytest.mark.parametrize("factor,expected", [
    ("industry_l0", [1, 1, 2, 2, 2, 3]),
    ("q_sales_yoy", [20, 30, 30, 30, 30, 40]),
    (WEIGHT, [0.2, 0.2, 0, 0, 0, 0.4]),
])
@pytest.mark.parametrize("fixed", [False, True])
def test_lookback_explicitly_loads_history_for_forward_filling(dolphin, factor, expected, fixed):
    reference = f"{factor}@{STOCK}" if fixed else factor
    codes = CODES if fixed else [STOCK]
    result = evaluate(dolphin, configuration(factors=[reference], codes=codes, lookback="P2D"))
    for code in codes:
        np.testing.assert_allclose(series(result, reference, code), expected, equal_nan=True)



def test_persistent_index_reference_matches_direct_index_query_and_dsl(dolphin):
    settings = DolphinSettings.from_env()
    common = dict(start_date="2026-04-27", end_date="2026-05-08", lookback="P10D")
    with execute_query({**common, "codes": [INDEX], "factors": ["close", "pct_chg"]}, session=dolphin, settings=settings) as result:
        expected = result.data.set_index("time").sort_index()
    with execute_query({**common, "codes": CODES, "factors": ["close", f"close@{INDEX}", f"pct_chg@{INDEX}"],
                        "derivatives": {
                            "index_return": direct("binary.div", left=f"pct_chg@{INDEX}", right=100.0),
                            "index_price_return": ts("unary.pct_change", f"close@{INDEX}", periods=1),
                            "excess": direct("binary.sub", left=ts("unary.pct_change", "close", periods=1), right="index_return"),
                        }}, session=dolphin, settings=settings) as result:
        actual = result.data
    assert not expected.empty
    assert expected.close.notna().any()
    assert set(actual.code) == set(CODES)
    assert not actual.duplicated(["time", "code"]).any()
    with execute_query({**common, "codes": [INDEX], "derivatives": {"price_return": ts("unary.pct_change", "close", periods=1)}}, session=dolphin, settings=settings) as result:
        price_returns = result.data.set_index("time").price_return
    for code in CODES:
        rows = actual.loc[actual.code == code].set_index("time").sort_index()
        assert rows.index.equals(expected.index)
        np.testing.assert_allclose(rows[f"close@{INDEX}"], expected.close, equal_nan=True)
        np.testing.assert_allclose(rows[f"pct_chg@{INDEX}"], expected.pct_chg, equal_nan=True)
        np.testing.assert_allclose(rows.index_return, expected.pct_chg / 100, equal_nan=True)
        np.testing.assert_allclose(rows.index_price_return, price_returns, equal_nan=True)
