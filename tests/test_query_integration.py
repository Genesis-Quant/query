"""Opt-in regressions using only session-local tables and read-only DFS queries."""

import json
import os

import numpy as np
import pandas as pd
import pytest

from query import DolphinSettings, create_session, execute_query
from query.apps.query.api import query_parameters
from query.database.compile.query.scripts import QUERY_SCRIPT


@pytest.fixture(scope="module")
def dolphin():
    if os.getenv("QUERY_TEST_DOLPHINDB") != "1":
        pytest.skip("requires explicit opt-in to the configured DolphinDB server")
    session = create_session(max_time=300)
    try:
        script = QUERY_SCRIPT.replace("def buildQuery(request)", "def queryTestBuild(request)")
        script = script.replace("sourceTable = loadTable(request.database, request.table)", "sourceTable = request.source")
        session.run(script)
        yield session
    finally:
        session.close()


def synthetic_source():
    rows = []
    dates = pd.to_datetime(["2026-04-29", "2026-04-30", "2026-05-06", "2026-05-07", "2026-05-08", "2026-05-11"])
    for index, day in enumerate(dates):
        for code in ("600000.SH", "000001.SZ"):
            for factor in ("open", "high", "low", "close"):
                value = np.nan if code == "000001.SZ" and day == pd.Timestamp("2026-05-06") else 10.0 + index
                rows.append({"time": day, "code": code, "factor": factor, "value": value})
            rows.append({"time": day, "code": code, "factor": "custom_feature", "value": 100.0 + index})
    return pd.DataFrame(rows)


def evaluate(session, *, lookforward="P20D", start="2026-04-30", end="2026-04-30"):
    settings = DolphinSettings(username="test", password="unused")
    request = query_parameters({
        "start_date": start, "end_date": end, "lookforward": lookforward,
        "codes": ["600000.SH", "000001.SZ"], "factors": ["close", "custom_feature"],
        "derivatives": {"next_close": {
            "type": "TS", "op": "unary.shift", "fields": {"col": "close"}, "params": {"periods": -1}
        }},
    }, settings)
    session.upload({"queryTestRows": synthetic_source(), "queryTestRequest": request})
    session.run('queryTestRequest["source"] = queryTestRows; queryTestResult = queryTestBuild(queryTestRequest); NULL')
    return session.run("queryTestResult.data"), session.run("queryTestResult.calendar")


def test_lookforward_reads_next_real_date_without_expanding_output(dolphin):
    result, calendar = evaluate(dolphin)
    assert len(result) == 2
    assert pd.DatetimeIndex(result.time).unique().tolist() == [pd.Timestamp("2026-04-30")]
    assert pd.DatetimeIndex(calendar).tolist() == [pd.Timestamp("2026-04-30")]
    assert result.set_index("code").loc["600000.SH", "next_close"] == 12.0
    assert pd.isna(result.set_index("code").loc["000001.SZ", "next_close"])
    assert result.custom_feature.eq(101.0).all()


def test_zero_lookforward_does_not_read_beyond_end(dolphin):
    result, calendar = evaluate(dolphin, lookforward="P0D")
    assert result.next_close.isna().all()
    assert len(calendar) == 1


def test_lookforward_preserves_end_date_after_weekend(dolphin):
    result, calendar = evaluate(dolphin, start="2026-05-08", end="2026-05-08")
    assert result.next_close.eq(15.0).all()
    assert result.time.eq(pd.Timestamp("2026-05-08")).all()
    assert len(calendar) == 1


def test_dfs_query_is_bounded_and_same_borrowed_session_can_be_reused(dolphin):
    settings = DolphinSettings.from_env()
    request = {
        "start_date": "2026-04-30", "end_date": "2026-05-08", "lookforward": "P20D",
        "codes": ["600000.SH"], "factors": ["close"],
        "derivatives": {"next_close": {
            "type": "TS", "op": "unary.shift", "fields": {"col": "close"}, "params": {"periods": -1}
        }},
    }
    with execute_query(request, session=dolphin, settings=settings) as result:
        actual = result.data
        assert 0 < len(actual) < 20
        assert actual.time.between(pd.Timestamp("2026-04-30"), pd.Timestamp("2026-05-08")).all()
        assert actual.code.eq("600000.SH").all()
        assert pd.notna(actual.next_close.iloc[-1])
    with execute_query(request, session=dolphin, settings=settings) as result:
        pd.testing.assert_frame_equal(actual, result.data)
    assert dolphin.run("1 + 1") == 2
    names = dolphin.run("defs().name")
    assert "buildQuery" in names
    assert "queryCompilation" in dolphin.run("objs(true).name")


def test_compilation_marker_prevents_reload_and_keeps_user_variables(dolphin):
    from query.database.session import initialize_session

    dolphin.upload({"queryUserValue": json.dumps({"keep": True})})
    initialize_session(dolphin)
    initialize_session(dolphin)
    assert dolphin.run("queryUserValue") == '{"keep": true}'
