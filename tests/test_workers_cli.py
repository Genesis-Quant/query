import importlib
import json
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from query.manage.workers import main
from query.utils.schema import CORE_COLUMNS
from query.workers import IndexDailyWorker
from query.workers.registry import WORKER_ORDER, normalize_worker_names


@pytest.mark.parametrize("name", ["dividend", "stock-dividend", "stockdividendworker"])
def test_wide_table_workers_are_not_registered(name):
    assert "dividend" not in WORKER_ORDER
    with pytest.raises(ValueError, match="未知 Worker"):
        normalize_worker_names([name])


def test_dry_run_never_runs_worker_or_opens_writer(monkeypatch, tmp_path):
    worker = Mock()
    worker.fetch_all.return_value = [pd.DataFrame({"value": [1.0, 2.0]})]
    worker.check.side_effect = lambda frame: frame
    cli = importlib.import_module("query.manage.workers")
    monkeypatch.setattr(cli, "create_workers", lambda *_: [worker])
    assert main(["daily", "--dry-run", "--output-dir", str(tmp_path)]) == 0
    worker.run.assert_not_called()
    worker.create_writer.assert_not_called()
    result = json.loads((tmp_path / "daily.json").read_text(encoding="utf-8"))
    assert result["status"] == "SUCCESS"
    assert result["metrics"]["dry_run"] is True


def test_index_worker_fetches_ohlc_into_factor_narrow_table(monkeypatch):
    module = importlib.import_module("query.workers.index_daily")
    worker = IndexDailyWorker(codes=["000300.SH"], start_date="2026-01-05", end_date="2026-01-05", overwrite=True)
    response = pd.DataFrame({"trade_date": ["20260105"], **{factor: [float(index + 1)] for index, factor in enumerate(worker.factors)}})
    worker.paginator.fetch = Mock(return_value=response)
    pro = Mock()
    monkeypatch.setattr(module, "get_pro", lambda: pro)
    result = worker.fetch_one("000300.SH", start_date=pd.Timestamp("2026-01-05"), end_date=pd.Timestamp("2026-01-05"))
    assert tuple(result.columns) == CORE_COLUMNS
    assert {"open", "high", "low", "close"} <= set(result.factor)
    assert result.code.eq("000300.SH").all()
    assert np.isfinite(result.value).all()
    assert worker.paginator.fetch.call_args.args[0] is pro.index_daily
    assert worker.paginator.fetch.call_args.kwargs["params"]["ts_code"] == "000300.SH"


def test_writer_credentials_do_not_fall_back_to_query_credentials(monkeypatch):
    from query.config import WorkerSettings

    monkeypatch.setattr(WorkerSettings, "RUNTIME_USERNAME", "reader")
    monkeypatch.setattr(WorkerSettings, "RUNTIME_PASSWORD", "reader-password")
    monkeypatch.setattr(WorkerSettings, "WORKER_USERNAME", None)
    monkeypatch.setattr(WorkerSettings, "WORKER_PASSWORD", None)
    with pytest.raises(RuntimeError, match="worker"):
        WorkerSettings.credentials("worker")


def test_cli_uses_explicit_current_directory_dotenv(monkeypatch, tmp_path):
    import dotenv

    from query.manage import main as command

    loader = Mock()
    monkeypatch.setattr(dotenv, "load_dotenv", loader)
    monkeypatch.chdir(tmp_path)
    assert command(["workers", "--list-workers"]) == 0
    loader.assert_called_once_with(tmp_path / ".env")
