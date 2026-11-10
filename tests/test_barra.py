from contextlib import nullcontext
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from query.config import BarraConfig
from query.database.tables.barra import BarraTableWriter
from query.workers.barra.industry import supplement_industry
from query.workers.barra.result import BarraResult
from query.workers.barra.source import dataset_query
from query.workers.barra.worker import BarraWorker
from query.workers.core.industry import SW_LEVEL1_TO_LEVEL0


def risk_tables(days):
    names = ["country", *BarraConfig.styles, *[
        "industry_" + code.split(".")[0] for code in SW_LEVEL1_TO_LEVEL0
    ]]
    return {
        "exposures": pd.DataFrame([
            (day, "A", name, float(name in ("country", "industry_801010")))
            for day in days for name in names
        ], columns=["time", "code", "factor", "value"]),
        "covariance": pd.DataFrame([
            (day, left, right, 0.01 if left == right else 0.0)
            for day in days for left in names for right in names
        ], columns=["time", "factor1", "factor2", "value"]),
        "specific": pd.DataFrame([
            (day, "A", 0.01) for day in days
        ], columns=["time", "code", "value"]),
    }


def test_segments_are_independent_clipped_natural_years():
    worker = BarraWorker(session=Mock(), start_date="2024-06-05", end_date="2026-03-06")
    assert [(str(a.date()), str(b.date())) for a, b in worker.segments()] == [
        ("2024-06-05", "2024-12-31"), ("2025-01-01", "2025-12-31"),
        ("2026-01-01", "2026-03-06"),
    ]


@pytest.mark.parametrize("codes", [[], "A", b"A"])
def test_invalid_model_universe_is_rejected(codes):
    with pytest.raises(ValueError, match="codes"):
        BarraWorker(session=Mock(), codes=codes)


def test_numpy_code_vector_is_supported():
    assert BarraWorker(session=Mock(), codes=np.array(["A", "B"])).codes == ["A", "B"]


def test_calculate_rejects_cross_year_without_running_a_query():
    session = Mock()
    worker = BarraWorker(session=session, start_date="2024-01-01", end_date="2025-01-05")
    with pytest.raises(ValueError, match="不跨年"):
        worker.calculate()
    session.run.assert_not_called()


def test_calendar_uses_both_market_and_benchmark_and_accepts_no_days():
    session = Mock()
    session.run.return_value = np.array([], dtype="datetime64[ms]")
    worker = BarraWorker(session=session)
    assert worker.get_calendar("2026-01-01", "2026-01-02").empty
    script = session.run.call_args.args[0]
    assert "reference.time in market.time" in script
    assert "market.time in reference.time" in script
    assert "max(reference.time)" not in script


def test_result_requires_the_exact_target_calendar():
    days = pd.to_datetime(["2026-01-05", "2026-01-07"])
    data = risk_tables(days)
    BarraTableWriter.check(data, calendar=days)
    with pytest.raises(ValueError, match="目标日历"):
        BarraTableWriter.check(data, calendar=pd.date_range("2026-01-05", "2026-01-07"))


def test_writer_deletes_only_dates_present_in_the_validated_input():
    days = pd.to_datetime(["2026-01-05", "2026-01-07"])
    data = risk_tables(days)
    session = Mock()
    responses = [None, None, None]
    for frame in data.values():
        responses.extend([None, len(frame), frame.groupby("time").size().rename("rows").reset_index()])
    session.run.side_effect = responses
    writer = BarraTableWriter(session)
    writer.prepared = True
    assert writer.write(data) == sum(map(len, data.values()))
    uploaded = session.upload.call_args_list[0].args[0]["barraWriteDates"]
    np.testing.assert_array_equal(uploaded, days.to_numpy(dtype="datetime64[ms]"))
    deletes = [call.args[0] for call in session.run.call_args_list if call.args[0].startswith("delete")]
    assert len(deletes) == 3
    assert all("time in barraWriteDates" in command for command in deletes)
    assert all("CoreData" not in command for command in deletes)


def test_invalid_data_is_rejected_before_writer_preparation():
    data = risk_tables(pd.to_datetime(["2026-01-05"]))
    data["specific"].loc[:, "value"] = -1.0
    session = Mock()
    with pytest.raises(ValueError):
        BarraTableWriter(session).write(data)
    session.upload.assert_not_called()
    session.run.assert_not_called()


def test_fetch_all_releases_one_segment_before_starting_the_next():
    events = []
    worker = BarraWorker(session=Mock(), start_date="2024-12-31", end_date="2025-01-02")

    class ExampleResult:
        def __init__(self, day):
            self.tables = risk_tables(pd.DatetimeIndex([day]))
            self.calendar = pd.DatetimeIndex([day])
            self.day = day

        def __enter__(self):
            return self

        def __exit__(self, *args):
            events.append(("released", self.day.year))

        def __getattr__(self, name):
            return self.tables[name]

    def calculate(start, end):
        events.append(("calculated", start.year))
        return ExampleResult(start)

    worker._calculate_segment = Mock(side_effect=calculate)
    frames = worker.fetch_all()
    next(frames)
    assert events == [("calculated", 2024)]
    next(frames)
    assert events == [("calculated", 2024), ("released", 2024), ("calculated", 2025)]
    frames.close()
    assert events[-1] == ("released", 2025)
    assert not worker.active


def test_missing_target_day_closes_result_and_stops_next_segment():
    worker = BarraWorker(session=Mock(), start_date="2024-01-01", end_date="2025-01-01")
    result = Mock()
    result.calendar = pd.date_range("2024-01-02", periods=3)
    for name, frame in risk_tables(pd.to_datetime(["2024-01-02", "2024-01-04"])).items():
        setattr(result, name, frame)
    context = Mock()
    context.__enter__ = Mock(return_value=result)
    context.__exit__ = Mock(return_value=False)
    worker._calculate_segment = Mock(return_value=context)
    # fetch_all accesses properties on the result itself rather than the context return value.
    context.calendar = result.calendar
    for name in ("exposures", "covariance", "specific"):
        setattr(context, name, getattr(result, name))
    with pytest.raises(ValueError, match="目标日历"):
        next(worker.fetch_all())
    context.__exit__.assert_called_once()
    assert worker._calculate_segment.call_count == 1
    assert not worker.active


def test_result_close_releases_only_its_objects_not_the_session():
    session = Mock()
    result = BarraResult(session=session)
    result.close()
    result.close()
    assert result.closed
    assert session.run.call_count == 1
    session.close.assert_not_called()


def history_source(rows):
    return pd.DataFrame(rows, columns=["index_code", "con_code", "in_date", "out_date"])


@pytest.mark.parametrize("level,expected", [(1, 801760.0), (0, 4.0)])
def test_direct_industry_intervals_are_used_only_for_missing_days(level, expected):
    missing = pd.DataFrame({"time": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
                            "code": "A"})
    source = history_source([
        ("801760.SI", "A", "20240102", "20240103"),
        ("801767.SI", "A", "20250929", None),
        ("801760.SI", "A", "20250929", None),
    ])
    with patch("query.workers.barra.industry.get_pro"), patch(
        "query.workers.barra.industry.Paginator.fetch", return_value=source,
    ):
        result = supplement_industry(missing, level=level)
    np.testing.assert_allclose(result.industry, [expected, expected, np.nan], equal_nan=True)
    assert result.columns.tolist() == ["time", "code", "industry"]


def test_conflicting_l1_is_not_inferred_from_a_deeper_classification():
    missing = pd.DataFrame({"time": pd.to_datetime(["2024-01-02"]), "code": "A"})
    source = history_source([
        ("801760.SI", "A", "20200101", None),
        ("801970.SI", "A", "20200101", None),
        ("857651.SI", "A", "20200101", None),
    ])
    with patch("query.workers.barra.industry.get_pro"), patch(
        "query.workers.barra.industry.Paginator.fetch", return_value=source,
    ):
        assert supplement_industry(missing, level=1).industry.isna().all()


def test_duplicate_intervals_for_same_l1_are_not_a_conflict():
    missing = pd.DataFrame({"time": pd.to_datetime(["2024-01-02"]), "code": "A"})
    source = history_source([
        ("801760.SI", "A", "20200101", None),
        ("801760.SI", "A", "20210101", None),
    ])
    with patch("query.workers.barra.industry.get_pro"), patch(
        "query.workers.barra.industry.Paginator.fetch", return_value=source,
    ):
        assert supplement_industry(missing, level=1).industry.tolist() == [801760.0]


def test_empty_industry_gap_does_not_call_upstream():
    missing = pd.DataFrame({"time": pd.to_datetime([]), "code": pd.Series(dtype=str)})
    with patch("query.workers.barra.industry.get_pro") as api:
        assert supplement_industry(missing, level=1).empty
    api.assert_not_called()


def test_barra_source_uses_existing_financial_fields_without_new_status_factors():
    request = dataset_query(pd.Timestamp("2026-01-05").date(), pd.Timestamp("2026-01-06").date(), ["A"])
    assert "n_income_attr_p_ttm" in request.source_factors()
    assert not any(name.startswith("valid_") for name in request.source_factors())


def test_industry_supplement_never_overwrites_primary_in_query_path():
    session = Mock()
    session.run.side_effect = [None, None, pd.DataFrame({
        "time": pd.to_datetime(["2024-01-02"]), "code": ["A"],
    }), None]
    worker = BarraWorker(session=session)
    result = Mock(data_ref="exampleData")
    with patch("query.workers.barra.worker.execute_query", side_effect=lambda *a, **k: nullcontext(result)), patch(
        "query.workers.barra.worker.supplement_industry",
        return_value=pd.DataFrame({"time": pd.to_datetime(["2024-01-02"]), "code": ["A"], "industry": [801760.0]}),
    ):
        worker._load_source(pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03"), ["A"])
    commands = [call.args[0] for call in session.run.call_args_list]
    assert "iif(isValid(industry) && industry>0,industry,supplement)" in commands[-1]
    assert not any(word in command for command in commands for word in ("tableInsert", "delete from", "truncate("))
