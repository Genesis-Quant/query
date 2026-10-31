from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from query.manage.workers import main
from query.workers.result import WorkerResult


class FakeWorker:
    def __init__(self, rows: int = 0, error: Exception | None = None) -> None:
        self.rows = rows
        self.error = error

    def __str__(self) -> str:
        return "daily"

    def run(self) -> int:
        if self.error is not None:
            raise self.error
        return self.rows


class WorkerResultTests(unittest.TestCase):
    def test_unselected_worker_writes_skipped_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch("query.manage.workers.create_workers") as create_workers:
                exit_code = main([
                    "daily",
                    "--selected-workers",
                    "st",
                    "--job-id",
                    "job-1",
                    "--output-dir",
                    directory,
                ])

            result = read_result(directory, "daily")
            self.assertEqual(exit_code, 0)
            self.assertEqual(result.status, "SKIPPED")
            self.assertFalse(result.metrics["selected"])
            create_workers.assert_not_called()

    def test_selected_worker_writes_success_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch(
                "query.manage.workers.create_workers",
                return_value=[FakeWorker(rows=12)],
            ):
                exit_code = main([
                    "daily",
                    "--selected-workers",
                    "daily",
                    "--job-id",
                    "job-1",
                    "--output-dir",
                    directory,
                ])

            result = read_result(directory, "daily")
            self.assertEqual(exit_code, 0)
            self.assertEqual(result.status, "SUCCESS")
            self.assertEqual(result.metrics["rows_written"], 12)
            self.assertEqual(result.attempts[0].executions[0].status, "SUCCESS")

    def test_failed_worker_writes_failure_before_nonzero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch(
                "query.manage.workers.create_workers",
                return_value=[FakeWorker(error=RuntimeError("boom"))],
            ):
                exit_code = main([
                    "daily",
                    "--job-id",
                    "job-1",
                    "--output-dir",
                    directory,
                ])

            result = read_result(directory, "daily")
            self.assertEqual(exit_code, 1)
            self.assertEqual(result.status, "FAILURE")
            self.assertEqual(result.error.type if result.error else None, "RuntimeError")
            self.assertEqual(result.error.message if result.error else None, "boom")


def read_result(directory: str, worker: str) -> WorkerResult:
    path = Path(directory) / f"{worker}.json"
    return WorkerResult.model_validate_json(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
