import os
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from query.workers.barra.merge import MERGE_SCRIPT
from query.workers.barra.model import MODEL_SCRIPT
from query.workers.barra.worker import BarraWorker

pytestmark = pytest.mark.skipif(
    os.getenv("QUERY_DDB_INTEGRATION") != "1",
    reason="Set QUERY_DDB_INTEGRATION=1 for read-only DolphinDB checks",
)


@pytest.fixture
def session():
    from scheme.data.dolphindb import create_session

    from query.config import WorkerSettings

    with create_session(WorkerSettings, role="runtime", max_time=180) as connection:
        yield connection


@pytest.mark.parametrize("missing", [None, "market", "benchmark"])
def test_calendar_detects_missing_trailing_day(session, missing):
    days = pd.date_range("2026-01-05", periods=3)
    rows = [(day, "A.SH", "close", 10.0) for day in days]
    rows += [(day, "000985.CSI", "pct_chg", 0.1) for day in days]
    source = pd.DataFrame(rows, columns=["time", "code", "factor", "value"])
    if missing:
        factor = "close" if missing == "market" else "pct_chg"
        source = source.loc[~(source.time.eq(days[-1]) & source.factor.eq(factor))]
    session.upload({"testCalendarSource": source})
    worker = BarraWorker(session=session, codes=["A.SH"])
    with patch("query.workers.barra.worker.core_table", return_value="testCalendarSource"):
        if missing:
            with pytest.raises(Exception, match="缺失"):
                worker.get_calendar(days[0], days[-1])
        else:
            assert worker.get_calendar(days[0], days[-1]).equals(pd.DatetimeIndex(days).as_unit("ms"))


def test_industry_substitution_preserves_primary_and_missing_state(session):
    original = pd.DataFrame({
        "time": pd.to_datetime(["2024-01-02"]*3), "code": ["A", "B", "C"],
        "industry": [801010.0, 0.0, 0.0],
    })
    supplement = pd.DataFrame({
        "time": pd.to_datetime(["2024-01-02"]*2), "code": ["A", "B"],
        "supplement": [801760.0, 801760.0],
    })
    session.upload({"barraIndustry": original, "barraIndustrySupplement": supplement})
    result = session.run("""
        select time,code,iif(isValid(industry) && industry>0,industry,supplement) as industry
            from lj(barraIndustry,barraIndustrySupplement,`time`code) order by code
    """)
    assert result.industry.iloc[:2].tolist() == [801010.0, 801760.0]
    assert pd.isna(result.industry.iloc[2])


@pytest.mark.parametrize("invalid", [None, "duplicate_style", "unestimated_industry"])
def test_regression_guards(session, invalid):
    session.run(MODEL_SCRIPT)
    rng = np.random.default_rng(20261110)
    size = 80
    exposures = pd.DataFrame({
        "code": [f"A{i}" for i in range(size)], "market_cap": rng.uniform(1, 20, size),
        "float_cap": rng.uniform(1, 10, size), "industry": [801010]*40+[801030]*40,
        "StyleA": rng.normal(size=size), "StyleB": rng.normal(size=size),
        "estimation_eligible": True,
    })
    returns = pd.DataFrame({
        "code": exposures.code, "return_day": rng.normal(0, 0.01, size), "return_valid": True,
    })
    if invalid == "duplicate_style":
        exposures["StyleB"] = exposures.StyleA
    elif invalid == "unestimated_industry":
        exposures.loc[40:, "estimation_eligible"] = False
    session.upload({
        "testExposures": exposures, "testReturns": returns,
        "testStyles": np.asarray(["StyleA", "StyleB"], dtype=str),
        "testIndustries": np.asarray([801010, 801030], dtype=np.int32),
    })
    expression = "getAllFactorValidate(testExposures,testReturns,testStyles,testIndustries,5)"
    if invalid:
        with pytest.raises(Exception, match="不满列秩|没有有效估计样本"):
            session.run(expression)
    else:
        result = session.run(expression)
        assert result["rank"] == 4
        assert len(result["residuals"]) == size
        assert np.isfinite(result["factors"].value).all()


def test_zero_mad_recipient_is_not_amplified(session):
    session.run(MERGE_SCRIPT)
    source = pd.DataFrame({
        "time": pd.to_datetime(["2026-01-05"]*5), "code": ["A", "B", "C", "D", "IPO"],
        "market_cap": [10.0]*5, "float_cap": [10.0]*5, "return_day": [0.0]*5,
        "benchmark_return": [0.0]*5, "return_valid": True, "market_valid": True,
        "eligible": [True]*4+[False], "sparse": [0.0]*4+[1e8],
    })
    industries = source[["time", "code"]].assign(industry=801010)
    session.upload({"testRaw": source, "testIndustry": industries})
    result = session.run('getRegTable(testRaw,testIndustry,["sparse"],0.5,2,false,5.0).data')
    assert result["sparse"].eq(0.0).all()
    assert len(result) == 5


def test_complete_in_memory_segment_produces_original_three_table_schema(session):
    from query.config import BarraConfig
    from query.database.tables.barra import BarraTableWriter
    from query.workers.barra.source import DESCRIPTORS
    from query.workers.core.industry import SW_LEVEL1_TO_LEVEL0

    rng = np.random.default_rng(20261110)
    calendar = pd.bdate_range("2026-01-02", periods=16).as_unit("ms")
    industries = np.asarray(sorted(int(code.split(".")[0]) for code in SW_LEVEL1_TO_LEVEL0))
    sector = np.repeat(industries, 4)
    codes = np.asarray([f"A{i:03d}" for i in range(len(sector))])
    size = len(codes)*len(calendar)
    source = pd.DataFrame({
        "time": np.repeat(calendar.to_numpy(), len(codes)), "code": np.tile(codes, len(calendar)),
        "market_cap": rng.uniform(10, 1000, size), "float_cap": rng.uniform(5, 500, size),
        "return_day": rng.normal(0, 0.01, size), "benchmark_return": rng.normal(0, 0.002, size),
        "return_valid": True, "market_valid": True, "eligible": True,
    })
    for name in DESCRIPTORS:
        source[name] = rng.normal(size=size)
    membership = source[["time", "code"]].assign(industry=np.tile(sector, len(calendar)))
    session.run(MERGE_SCRIPT)
    session.run(MODEL_SCRIPT)
    session.upload({
        "testSegmentRaw": source, "testSegmentIndustry": membership,
        "testSegmentCalendar": calendar.to_numpy(), "testSegmentDescriptors": np.asarray(DESCRIPTORS),
        "testSegmentStyles": np.asarray(BarraConfig.styles),
        "testSegmentFirst": {name: np.asarray(values) for name, values in BarraConfig.first_factors.items()},
        "testSegmentSecond": {name: np.asarray(values) for name, values in BarraConfig.second_factors.items()},
        "testSegmentRequest": {
            "start": calendar[-3].to_datetime64(), "end": calendar[-1].to_datetime64(),
            "minimumStocks": np.int32(40), "covarianceWindow": np.int32(10),
            "specificWindow": np.int32(10), "covarianceHalfLife": 5.0, "specificHalfLife": 5.0,
            "minimumObservations": np.int32(5), "minimumSpecificObservations": np.int32(5),
            "specificPeerFallback": True, "specificPeerMinStocks": np.int32(3),
            "specificShortObservations": np.int32(2), "lags": np.int32(2),
            "varianceFloor": 1e-8, "shrink": True, "industries": industries.astype(np.int32),
        },
    })
    session.run("""
        testSegmentMerge=getRegTable(testSegmentRaw,testSegmentIndustry,testSegmentDescriptors,0.5,40,false,5.0)
        testSegmentFactors=getFSLevelFactor(testSegmentMerge.data,testSegmentFirst,testSegmentSecond,5.0)
        testSegmentRisk=getRiskTables(testSegmentFactors,testSegmentRaw,testSegmentCalendar,testSegmentStyles,testSegmentRequest)
        NULL
    """)
    data = {name: session.run(f"testSegmentRisk.{name}") for name in ("exposures", "covariance", "specific")}
    BarraTableWriter.check(data, calendar=calendar[-3:])
    assert len(data["exposures"]) == 3*len(codes)*40
    assert len(data["covariance"]) == 3*40*40
    assert len(data["specific"]) == 3*len(codes)
    diagnostics = session.run("testSegmentRisk.regression")
    assert diagnostics["rank"].eq(39).all()
    assert np.isfinite(data["specific"].value).all()
