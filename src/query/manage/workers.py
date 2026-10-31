"""实现数据写入 Worker 管理命令。"""

import argparse
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from query.workers.registry import (
    DATE_WORKERS,
    STOCK_WORKERS,
    WORKER_DESCRIPTIONS,
    WORKER_ORDER,
    normalize_worker_names,
)


def positive_int(value: str) -> int:
    """解析大于零的整数命令行参数。"""
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("必须大于 0")
    return result


def nonnegative_int(value: str) -> int:
    """解析不小于零的整数命令行参数。"""
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError("不能小于 0")
    return result


def nonnegative_float(value: str) -> float:
    """解析不小于零的浮点命令行参数。"""
    result = float(value)
    if result < 0:
        raise argparse.ArgumentTypeError("不能小于 0")
    return result


def build_parser(*, prog: str | None = None) -> argparse.ArgumentParser:
    """创建 Worker 命令行解析器。"""
    parser = argparse.ArgumentParser(
        prog=prog,
        description="运行指定 Worker 或依次运行全部 Worker。",
        epilog=(
            "示例：\n"
            "  query workers daily adj-factor\n"
            "  python -m query workers income --codes 000001.SZ,600000.SH\n"
            "  python -m query workers index-daily "
            "--index-code 000300.SH --dry-run\n"
            "  python -m query workers index-weight "
            "--index-code 000300.SH --dry-run\n"
            "  python -m query workers all "
            "--start-date 2025-01-01 --overwrite"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "workers",
        nargs="*",
        metavar="WORKER",
        help="Worker 名称；使用 all 运行全部，使用 --list-workers 查看列表",
    )
    parser.add_argument(
        "--list-workers",
        action="store_true",
        help="列出可用 Worker 后退出",
    )
    parser.add_argument("--start-date", help="更新起始日期")
    parser.add_argument("--end-date", help="更新结束日期，默认今天")
    parser.add_argument(
        "--codes",
        action="append",
        metavar="CODE[,CODE...]",
        help="限制按代码 Worker 的股票或基金代码，可重复传入",
    )
    parser.add_argument(
        "--index-code",
        action="append",
        metavar="CODE[,CODE...]",
        help=(
            "index-daily、index-weight 的指数代码，"
            "默认使用配置文件中的 INDEX_CODES"
        ),
    )
    parser.add_argument("--threads", type=positive_int, help="并发线程数")
    parser.add_argument(
        "--throttle",
        type=nonnegative_int,
        help="每秒最大 API 请求数，0 表示不限速",
    )
    parser.add_argument(
        "--max-retries",
        type=positive_int,
        help="单次请求最大重试次数",
    )
    parser.add_argument(
        "--retry-interval",
        type=nonnegative_float,
        help="重试间隔秒数",
    )
    parser.add_argument(
        "--batch-size",
        type=positive_int,
        help="单次写入的最大行数",
    )
    parser.add_argument(
        "--chunk-size",
        type=positive_int,
        help="DateWorker 每个完整提交块包含的自然日数",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "忽略增量水位并重新抓取指定区间；同键数据由 TSDB 保留最新值，"
            "不会预先删除旧记录"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="抓取并校验数据但不创建 writer、不写入数据库",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="任一 Worker 失败后立即停止；默认继续运行其余 Worker",
    )
    parser.add_argument(
        "--job-id",
        default="",
        help="可选工作流任务标识，仅写入结构化结果",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="可选 JSON 结果目录；空字符串表示不输出结果",
    )
    parser.add_argument(
        "--selected-workers",
        default="",
        metavar="WORKER[,WORKER...]",
        help="工作流选择的 Worker；空字符串表示执行全部",
    )
    return parser


def split_values(
        values: Sequence[str] | None,
        location: str,
) -> tuple[str, ...] | None:
    """拆分可重复的逗号列表，在保持顺序的同时去重。"""
    if values is None:
        return None
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        parts = [part.strip() for part in value.split(",")]
        if any(not part for part in parts):
            raise ValueError(f"{location} 不能包含空值")
        for part in parts:
            if part not in seen:
                result.append(part)
                seen.add(part)
    return tuple(result)


def normalize_worker_selection(value: str) -> tuple[str, ...] | None:
    """解析工作流传入的逗号列表；空值表示不限制 Worker。"""
    if not value.strip():
        return None
    parts = tuple(part.strip() for part in value.split(","))
    if any(not part for part in parts):
        raise ValueError("--selected-workers 不能包含空值")
    return normalize_worker_names(parts)


def worker_kwargs(arguments: argparse.Namespace) -> dict[str, Any]:
    """返回仅包含用户显式配置值的公共 Worker 构造参数。"""
    result: dict[str, Any] = {"overwrite": arguments.overwrite}
    mappings = {
        "start_date": arguments.start_date,
        "end_date": arguments.end_date,
        "threads": arguments.threads,
        "throttle": arguments.throttle,
        "max_retries": arguments.max_retries,
        "retry_interval": arguments.retry_interval,
        "batch_size": arguments.batch_size,
    }
    result.update({
        name: value
        for name, value in mappings.items()
        if value is not None
    })
    return result


def create_workers(
        names: Sequence[str],
        arguments: argparse.Namespace,
) -> list[Any]:
    """根据规范名称创建按执行顺序排列的 Worker 实例。"""
    from query.config import INDEX_CODES
    from query.workers import (
        FundAdjFactorWorker,
        FundDailyWorker,
        IndexDailyWorker,
        IndexWeightWorker,
        IndustryWorker,
        StockAdjFactorWorker,
        StockBalanceSheetWorker,
        StockCashflowWorker,
        StockDailyBasicWorker,
        StockDailyWorker,
        StockFinaIndicatorWorker,
        StockHfqWorker,
        StockIncomeWorker,
        StockLimitWorker,
        StockSTWorker,
    )

    date_types = {
        "daily": StockDailyWorker,
        "limit": StockLimitWorker,
        "daily-basic": StockDailyBasicWorker,
        "adj-factor": StockAdjFactorWorker,
        "st": StockSTWorker,
    }
    stock_types = {
        "fund-adj-factor": FundAdjFactorWorker,
        "fund-daily": FundDailyWorker,
        "hfq": StockHfqWorker,
        "balance-sheet": StockBalanceSheetWorker,
        "income": StockIncomeWorker,
        "cashflow": StockCashflowWorker,
        "fina-indicator": StockFinaIndicatorWorker,
    }

    common = worker_kwargs(arguments)
    date_arguments = dict(common)
    if arguments.chunk_size is not None:
        date_arguments["chunk_size"] = arguments.chunk_size
    stock_arguments = dict(common)
    codes = split_values(arguments.codes, "--codes")
    if codes is not None:
        stock_arguments["codes"] = codes

    index_codes = split_values(arguments.index_code, "--index-code")
    if index_codes is None:
        index_codes = tuple(INDEX_CODES)

    workers: list[Any] = []
    for name in names:
        if name == "industry":
            workers.append(IndustryWorker(**common))
        elif name in date_types:
            workers.append(date_types[name](**date_arguments))
        elif name == "index-daily":
            if not index_codes:
                raise ValueError(
                    "没有可用指数代码，请配置 INDEX_CODES 或传入 --index-code"
                )
            workers.append(IndexDailyWorker(codes=index_codes, **common))
        elif name in stock_types:
            workers.append(stock_types[name](**stock_arguments))
        elif name == "index-weight":
            if not index_codes:
                raise ValueError(
                    "没有可用指数代码，请配置 INDEX_CODES 或传入 --index-code"
                )
            workers.extend(
                IndexWeightWorker(index_code, **date_arguments)
                for index_code in index_codes
            )
        else:
            raise AssertionError(f"未注册 Worker：{name}")
    return workers


def dry_run_worker(worker: Any) -> int:
    """抓取并校验一个 Worker 的全部计划结果，但不执行任何写入。"""
    from query.utils.logging import logger

    started = time.perf_counter()
    rows = 0
    frames = 0
    logger.info(f"{worker} 开始 dry-run：不会写入数据库")
    for data in worker.fetch_all():
        frame = worker.check(data)
        rows += len(frame)
        frames += 1
    elapsed = time.perf_counter() - started
    logger.success(
        f"{worker} dry-run 完成：结果={rows:,}行，"
        f"批次={frames:,}，耗时={elapsed:.2f}秒"
    )
    return rows


def validate_arguments(
        parser: argparse.ArgumentParser,
        names: Sequence[str],
        arguments: argparse.Namespace,
) -> None:
    """拒绝对所选 Worker 没有意义的专用参数。"""
    selected = set(names)
    if arguments.codes and not selected.intersection(STOCK_WORKERS):
        parser.error("--codes 仅适用于按代码 Worker")
    if (
            arguments.index_code
            and not selected.intersection({"index-daily", "index-weight"})
    ):
        parser.error("--index-code 仅适用于 index-daily、index-weight")
    if (
            arguments.chunk_size is not None
            and not selected.intersection(DATE_WORKERS)
    ):
        parser.error("--chunk-size 仅适用于 DateWorker")


def print_workers() -> None:
    """打印规范 Worker 名称和用途。"""
    width = max(map(len, WORKER_ORDER))
    for name in WORKER_ORDER:
        print(f"{name:<{width}}  {WORKER_DESCRIPTIONS[name]}")


def main(
        argv: Sequence[str] | None = None,
        *,
        prog: str | None = None,
) -> int:
    """解析命令行、依次运行 Worker，并返回进程退出码。"""
    parser = build_parser(prog=prog)
    arguments = parser.parse_args(argv)
    if arguments.list_workers:
        print_workers()
        return 0

    try:
        requested_names = normalize_worker_names(arguments.workers)
        selection = normalize_worker_selection(arguments.selected_workers)
        split_values(arguments.codes, "--codes")
        split_values(arguments.index_code, "--index-code")
    except ValueError as error:
        parser.error(str(error))
    validate_arguments(parser, requested_names, arguments)
    names = (
        requested_names
        if selection is None
        else tuple(name for name in requested_names if name in selection)
    )

    from query.utils.logging import logger
    from query.workers.result import (
        WorkerAttempt,
        WorkerExecutionResult,
        WorkerResult,
        WorkerStatus,
        worker_error,
        write_worker_result,
    )

    result_worker = (
        requested_names[0]
        if len(requested_names) == 1
        else "workers"
    )
    if not names:
        started_at = datetime.now(UTC)
        started = time.perf_counter()
        logger.info(
            f"Worker 未被本次工作流选中，跳过执行：{result_worker}"
        )
        finished_at = datetime.now(UTC)
        elapsed = time.perf_counter() - started
        result = WorkerResult(
            job_id=arguments.job_id.strip() or None,
            worker=result_worker,
            status="SKIPPED",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=elapsed,
            metrics={
                "rows_written": 0,
                "workers_total": 0,
                "workers_completed": 0,
                "workers_succeeded": 0,
                "workers_failed": 0,
                "workers_cancelled": 0,
                "selected": False,
                "dry_run": arguments.dry_run,
            },
            attempts=[
                WorkerAttempt(
                    number=1,
                    status="SKIPPED",
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_seconds=elapsed,
                    rows_written=0,
                    executions=[],
                )
            ],
        )
        result_path = write_worker_result(arguments.output_dir, result)
        if result_path is not None:
            logger.info(f"Worker 结构化结果已写入：{result_path}")
        return 0

    try:
        workers = create_workers(names, arguments)
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    mode = "dry-run" if arguments.dry_run else "写入"
    if arguments.overwrite:
        logger.warning(
            "已启用覆盖模式：将忽略增量水位并重新抓取指定日期区间；"
            "不会预先删除数据库记录"
        )
    logger.info(
        f"Worker 任务开始：模式={mode}，"
        f"任务={len(workers):,}，选择={list(names)}"
    )

    started_at = datetime.now(UTC)
    started = time.perf_counter()
    total = 0
    failures: list[str] = []
    executions: list[WorkerExecutionResult] = []
    interrupted = False
    for number, worker in enumerate(workers, start=1):
        logger.info(f"运行 Worker {number:,}/{len(workers):,}：{worker}")
        execution_started_at = datetime.now(UTC)
        execution_started = time.perf_counter()
        try:
            rows = (
                dry_run_worker(worker)
                if arguments.dry_run
                else worker.run()
            )
        except KeyboardInterrupt as error:
            logger.warning(f"Worker 任务被用户中断：{worker}")
            execution_finished_at = datetime.now(UTC)
            executions.append(
                WorkerExecutionResult(
                    name=str(worker),
                    status="CANCELLED",
                    rows_written=0,
                    started_at=execution_started_at,
                    finished_at=execution_finished_at,
                    duration_seconds=time.perf_counter() - execution_started,
                    error=worker_error(error),
                )
            )
            interrupted = True
            break
        except Exception as error:
            failures.append(
                f"{worker}: {type(error).__name__}: {error}"
            )
            logger.exception(f"Worker 运行失败：{worker}")
            execution_finished_at = datetime.now(UTC)
            executions.append(
                WorkerExecutionResult(
                    name=str(worker),
                    status="FAILURE",
                    rows_written=0,
                    started_at=execution_started_at,
                    finished_at=execution_finished_at,
                    duration_seconds=time.perf_counter() - execution_started,
                    error=worker_error(error),
                )
            )
            if arguments.fail_fast:
                break
        else:
            total += rows
            execution_finished_at = datetime.now(UTC)
            executions.append(
                WorkerExecutionResult(
                    name=str(worker),
                    status="SUCCESS",
                    rows_written=rows,
                    started_at=execution_started_at,
                    finished_at=execution_finished_at,
                    duration_seconds=time.perf_counter() - execution_started,
                )
            )

    elapsed = time.perf_counter() - started
    finished_at = datetime.now(UTC)
    status: WorkerStatus = "CANCELLED" if interrupted else "FAILURE" if failures else "SUCCESS"
    result_error = next(
        (
            execution.error
            for execution in reversed(executions)
            if execution.error is not None
        ),
        None,
    )
    result = WorkerResult(
        job_id=arguments.job_id.strip() or None,
        worker=result_worker,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=elapsed,
        metrics={
            "rows_written": total,
            "workers_total": len(workers),
            "workers_completed": len(executions),
            "workers_succeeded": sum(
                execution.status == "SUCCESS" for execution in executions
            ),
            "workers_failed": sum(
                execution.status == "FAILURE" for execution in executions
            ),
            "workers_cancelled": sum(
                execution.status == "CANCELLED" for execution in executions
            ),
            "selected": True,
            "dry_run": arguments.dry_run,
        },
        attempts=[
            WorkerAttempt(
                number=1,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=elapsed,
                rows_written=total,
                executions=executions,
                error=result_error,
            )
        ],
        error=result_error,
    )
    result_path = write_worker_result(arguments.output_dir, result)
    if result_path is not None:
        logger.info(f"Worker 结构化结果已写入：{result_path}")

    if interrupted:
        return 130
    if failures:
        logger.error(
            f"Worker 任务完成但存在失败：成功结果={total:,}行，"
            f"失败={len(failures):,}，耗时={elapsed:.2f}秒；"
            + "；".join(failures)
        )
        return 1

    result_name = "校验" if arguments.dry_run else "写入"
    logger.success(
        f"Worker 任务全部完成：{result_name}={total:,}行，"
        f"任务={len(workers):,}，耗时={elapsed:.2f}秒"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
