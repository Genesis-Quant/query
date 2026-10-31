"""Worker 命令的结构化 JSON 执行结果。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from query.utils.files import atomic_write_text

WorkerStatus = Literal["SUCCESS", "FAILURE", "CANCELLED", "SKIPPED"]


class WorkerError(BaseModel):
    """可安全写入结果文件的错误摘要。"""

    model_config = ConfigDict(extra="forbid", strict=True)

    type: str
    message: str


class WorkerExecutionResult(BaseModel):
    """一次命令中一个具体 Worker 实例的执行结果。"""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    status: WorkerStatus
    rows_written: int = Field(ge=0)
    started_at: datetime
    finished_at: datetime
    duration_seconds: float = Field(ge=0)
    error: WorkerError | None = None


class WorkerAttempt(BaseModel):
    """DolphinScheduler 重试产生的一次进程级执行。"""

    model_config = ConfigDict(extra="forbid", strict=True)

    number: int = Field(ge=1)
    status: WorkerStatus
    started_at: datetime
    finished_at: datetime
    duration_seconds: float = Field(ge=0)
    rows_written: int = Field(ge=0)
    executions: list[WorkerExecutionResult]
    error: WorkerError | None = None


class WorkerResult(BaseModel):
    """一个 Worker Task 固定文件中的最新状态和重试历史。"""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    job_id: str | None = None
    workflow: Literal["incremental-update"] = "incremental-update"
    worker: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    status: WorkerStatus
    started_at: datetime
    finished_at: datetime
    duration_seconds: float = Field(ge=0)
    metrics: dict[str, Any]
    attempts: list[WorkerAttempt]
    error: WorkerError | None = None


def write_worker_result(output_dir: str, result: WorkerResult) -> Path | None:
    """输出目录非空时原子写入 JSON；空字符串明确表示禁用输出。"""
    normalized = output_dir.strip()
    if not normalized:
        return None

    directory = Path(normalized).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{result.worker}.json"
    result = merge_previous_attempts(destination, result)
    return atomic_write_text(destination, result.model_dump_json(indent=2))


def merge_previous_attempts(
        destination: Path,
        result: WorkerResult,
) -> WorkerResult:
    """同一任务重试时保留旧尝试；不兼容的旧文件由本次结果替换。"""
    if result.job_id is None or not destination.is_file():
        return result
    try:
        previous = WorkerResult.model_validate_json(
            destination.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return result
    if previous.job_id != result.job_id or previous.worker != result.worker:
        return result

    next_number = len(previous.attempts) + 1
    latest_attempt = result.attempts[-1].model_copy(
        update={"number": next_number}
    )
    return result.model_copy(
        update={"attempts": [*previous.attempts, latest_attempt]}
    )


def worker_error(error: BaseException) -> WorkerError:
    """不包含 traceback 的稳定错误表示。"""
    return WorkerError(type=type(error).__name__, message=str(error))


__all__ = [
    "WorkerAttempt",
    "WorkerError",
    "WorkerExecutionResult",
    "WorkerResult",
    "WorkerStatus",
    "worker_error",
    "write_worker_result",
]
