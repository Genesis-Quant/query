import importlib
import json
import re
from datetime import timedelta
from unittest.mock import Mock

import pandas as pd
import pytest
from pydantic import ValidationError

from query import FactorQuery, compile
from query.apps.query.api import query_parameters
from query.database.compile import DolphinDBFunction, collect_functions
from query.settings import DolphinSettings

sessions = importlib.import_module("query.database.session")
api = importlib.import_module("query.apps.query.api")


def settings(**values):
    return DolphinSettings(username="test", password="not-a-secret", **values)


def request(**overrides):
    return dict(start_date="2026-04-30", end_date="2026-05-08", codes=["600000.SH"], factors=["close"], **overrides)


@pytest.mark.parametrize("name", ["lookback", "lookforward"])
@pytest.mark.parametrize("value", [True, False, 0, 1, 1.5, None, [], {}, "invalid", "-P1D", timedelta(days=-1)])
def test_durations_reject_invalid_inputs(name, value):
    with pytest.raises(ValidationError):
        FactorQuery.model_validate(request(**{name: value}))


def test_compile_is_cached_self_contained_and_deterministic():
    first = compile()
    assert first is compile()
    assert not re.search(r"^\s*(?:module\s|use\s+(?:query|common|factor)\b)", first, re.M)
    names = re.findall(r"^def (\w+)\(", first, re.M)
    assert len(names) == len(set(names)) > 250
    assert "buildQuery" in names
    assert "build_factor_source" in names
    assert "require_table_columns" in names


def test_cross_module_dependencies_are_inlined_before_callers():
    dependency = DolphinDBFunction(module="common", definition="def shared() { return 1 }")
    root = DolphinDBFunction(module="query", definition="def outer() { return shared() }", dependencies=(dependency,))
    assert [function.name for function in collect_functions([root], "query")] == ["shared", "outer"]


def test_conflicting_global_function_names_are_rejected():
    left = DolphinDBFunction(module="common", definition="def shared() { return 1 }")
    right = DolphinDBFunction(module="query", definition="def shared() { return 2 }")
    with pytest.raises(ValueError, match="重复定义"):
        collect_functions([left, right])


def test_each_session_loads_compilation_once(monkeypatch):
    state = {}
    session = Mock()
    session.run.side_effect = lambda script: (
        "queryCompilation" in state if "in objs(true)" in script
        else state.get("queryCompilation")
    )
    session.upload.side_effect = state.update
    sessions.initialize_session(session)
    sessions.initialize_session(session)
    assert sum(call.args[0] == sessions.build_script() for call in session.run.call_args_list) == 1
    other = Mock()
    other.run.return_value = None
    sessions.initialize_session(other)
    assert sum(call.args[0] == sessions.build_script() for call in other.run.call_args_list) == 1


def test_connect_preloads_before_return_and_initialization_failure_closes(monkeypatch):
    connection = Mock()
    connection.connect.return_value = True
    monkeypatch.setattr(sessions.dolphindb, "session", lambda: connection)
    monkeypatch.setattr(sessions, "redirect_session_output", lambda _: None)
    assert sessions.create_session(settings()) is connection
    connection.run.assert_any_call(sessions.build_script())
    connection.close.assert_not_called()
    connection.run.side_effect = RuntimeError("compile failure")
    with pytest.raises(RuntimeError, match="compile failure"):
        sessions.create_session(settings())
    connection.close.assert_called_once()


def test_endpoint_failure_closes_before_trying_next(monkeypatch):
    first, second = Mock(), Mock()
    first.connect.side_effect = ConnectionError("unavailable")
    second.connect.return_value = True
    connections = iter([first, second])
    monkeypatch.setattr(sessions.dolphindb, "session", lambda: next(connections))
    monkeypatch.setattr(sessions, "redirect_session_output", lambda _: None)
    assert sessions.create_session(settings(endpoints=("first:8848", "second:8848"))) is second
    first.close.assert_called_once()
    second.run.assert_any_call(sessions.build_script())


def test_lookforward_expands_only_calculation_domain_and_accepts_custom_factors():
    parameters = query_parameters(dict(start_date="2026-04-30", end_date="2026-05-08", codes=["600000.SH"], factors=["custom_feature"], lookback="P110D", lookforward="P20D"), settings(database="dfs://Custom", table="features"))
    assert parameters["start"] == pd.Timestamp("2026-01-10")
    assert parameters["end"] == pd.Timestamp("2026-05-29")
    assert parameters["outputStart"] == pd.Timestamp("2026-04-30")
    assert parameters["outputEnd"] == pd.Timestamp("2026-05-09")
    assert parameters["factors"].tolist() == ["custom_feature"]
    assert parameters["database"] == "dfs://Custom"
    assert parameters["table"] == "features"


def test_query_uses_local_definitions_and_borrowed_session_survives(monkeypatch):
    session = Mock()
    monkeypatch.setattr(api, "redirect_session_output", lambda _: None)
    monkeypatch.setattr(api, "initialize_session", lambda _: None)
    with api.execute_query(request(), session=session, settings=settings()) as result:
        assert not result.owns_session
        assert result.data_ref == api.DATA_REF
    session.close.assert_not_called()
    scripts = "\n".join(call.args[0] for call in session.run.call_args_list)
    assert "use query" not in scripts
    assert "buildQuery(queryRequest)" in scripts
    assert f'undef({json.dumps(api.DATA_REF)}, VAR)' in scripts
    assert "undef(\"buildQuery\"" not in scripts


def test_owned_session_is_closed_with_result(monkeypatch):
    session = Mock()
    monkeypatch.setattr(api, "create_session", lambda *_: session)
    monkeypatch.setattr(api, "redirect_session_output", lambda _: None)
    monkeypatch.setattr(api, "initialize_session", lambda _: None)
    with api.execute_query(request(), settings=settings()) as result:
        assert result.owns_session
    session.close.assert_called_once()


def test_failed_active_result_guard_never_cleans_existing_data(monkeypatch):
    session = Mock()
    session.run.side_effect = RuntimeError("active query")
    monkeypatch.setattr(api, "redirect_session_output", lambda _: None)
    with pytest.raises(RuntimeError, match="active query"):
        api.execute_query(request(), session=session, settings=settings())
    assert session.run.call_count == 1
    session.close.assert_not_called()


def test_query_error_is_not_replaced_by_cleanup_error(monkeypatch):
    session = Mock()
    session.run.side_effect = [None, RuntimeError("original query failure"), RuntimeError("cleanup failure"), RuntimeError("result cleanup failure")]
    monkeypatch.setattr(api, "redirect_session_output", lambda _: None)
    monkeypatch.setattr(api, "initialize_session", lambda _: None)
    with pytest.raises(RuntimeError, match="original query failure"):
        api.execute_query(request(), session=session, settings=settings())
    session.close.assert_not_called()


def test_context_error_is_not_replaced_by_close_error():
    from query.apps.query.result import QueryResult

    session = Mock()
    session.close.side_effect = RuntimeError("close failure")
    result = QueryResult(session=session, source_ref="source", computed_ref="computed",
                         filtered_ref="filtered", data_ref="data", calendar_ref="dates",
                         owns_session=True)
    with pytest.raises(ValueError, match="calculation failure"):
        with result:
            raise ValueError("calculation failure")
    assert result.closed


def test_session_initialization_error_is_not_replaced_by_close_error(monkeypatch):
    session = Mock()
    session.connect.return_value = True
    session.close.side_effect = RuntimeError("close failure")
    monkeypatch.setattr(sessions.dolphindb, "session", lambda: session)
    monkeypatch.setattr(sessions, "redirect_session_output", lambda _: None)
    monkeypatch.setattr(sessions, "initialize_session", Mock(side_effect=ValueError("invalid DOS")))
    with pytest.raises(ValueError, match="invalid DOS"):
        sessions.create_session(settings())
    session.close.assert_called_once()
