"""独立Query命令行；SDK连接只在Worker更新入口创建。"""

import argparse
import sys
import time
from collections.abc import Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import Any, override

import dolphindb

from query.config import DolphinSettings, WorkerSettings
from query.utils.logging import logger
from query.workers.registry import (
    DATE_WORKERS,
    STOCK_WORKERS,
    WORKER_DESCRIPTIONS,
    WORKER_ORDER,
    normalize_worker_names,
)


class WorkerLogSink(dolphindb.logger.Sink):
    """把独立更新命令的SDK输出送入已有日志，不修改Loguru配置。"""

    def __init__(self) -> None:
        super().__init__("loguru")

    @override
    def handle(self, message: Any) -> None:
        logger.log(message.level.name, message.log.rstrip("\r\n"))

    @override
    def flush(self) -> None:
        return None


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


def build_workers_parser(*, prog: str | None = None) -> argparse.ArgumentParser:
    """创建 Worker 命令行解析器。"""
    parser = argparse.ArgumentParser(
        prog=prog,
        description="运行指定 Worker 或依次运行全部 Worker。",
        epilog=(
            "示例：\n"
            "  query workers daily adj-factor\n"
            "  query workers income --codes 000001.SZ,600000.SH\n"
            "  query workers index-daily "
            "--index-code 000300.SH --dry-run\n"
            "  query workers index-weight "
            "--index-code 000300.SH --dry-run\n"
            "  query workers all "
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
    parser.add_argument("--start-date", help="更新起始日期，Barra默认2016-01-01并按自然年完整重算，其余默认DATA_START_DATE并按水位增量更新")
    parser.add_argument("--end-date", help="更新结束日期，默认今天")
    parser.add_argument(
        "--codes",
        action="append",
        metavar="CODE[,CODE...]",
        help="限制按代码 Worker 或 Barra 的证券域，可重复传入",
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
            "CoreData忽略增量水位并重算指定区间；"
            "Barra始终按start/end分年独立重算并上传整段三表，不使用水位"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="抓取并校验数据，不建库、不执行写入",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="持久日志文件；默认 output/workers/时间-进程-随机标识.log，不覆盖已有文件",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        default=True,
        help="任一 Worker 失败后立即停止（默认行为）",
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
        *,
        session: Any | None = None,
        settings: type[DolphinSettings] = DolphinSettings,
) -> list[Any]:
    """根据规范名称创建按执行顺序排列的 Worker 实例。"""
    from query.config import INDEX_CODES
    from query.workers import (
        BarraWorker,
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
    common["session"] = session
    common["settings"] = settings
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
        if name == "barra":
            barra_arguments = {
                key: value for key, value in common.items()
                if key in {"session", "settings", "start_date", "end_date", "batch_size"}
            }
            workers.append(BarraWorker(codes=codes, **barra_arguments))
        elif name == "industry":
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
    results = worker.fetch_all()
    try:
        for data in results:
            frame = worker.check(data)
            rows += sum(len(table) for table in frame.values()) if isinstance(frame, dict) else len(frame)
            frames += 1
    finally:
        failed = sys.exception() is not None
        close = getattr(results, "close", None)
        if close is not None:
            try:
                close()
            except Exception as error:
                if not failed:
                    raise
                logger.warning(f"dry-run失败后回收结果异常：{type(error).__name__}")
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
    if arguments.codes and not selected.intersection(STOCK_WORKERS | {"barra"}):
        parser.error("--codes 仅适用于按代码 Worker 或 Barra")
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


def run_workers(
        argv: Sequence[str] | None = None,
        *,
        prog: str | None = None,
        session: Any | None = None,
        settings: type[WorkerSettings] = WorkerSettings,
        log_path: Path | None = None,
) -> int:
    """独立运行更新命令；已有会话可注入，SDK连接只在本入口创建。"""
    parser = build_workers_parser(prog=prog)
    arguments = parser.parse_args(argv)
    if arguments.list_workers:
        print_workers()
        return 0

    try:
        names = normalize_worker_names(arguments.workers)
        split_values(arguments.codes, "--codes")
        split_values(arguments.index_code, "--index-code")
    except ValueError as error:
        parser.error(str(error))
    validate_arguments(parser, names, arguments)

    from query.utils.logging import add_worker_file_log

    if log_path is None:
        try:
            log_path = add_worker_file_log(arguments.log_file)
        except OSError as error:
            parser.error(f"无法创建运行日志：{type(error).__name__}")
    logger.info(f"Worker 运行日志：{log_path}")
    owns_session = session is None
    try:
        with ExitStack() as connections:
            if session is None and not (arguments.dry_run and arguments.overwrite and "barra" not in names):
                if not settings.worker_username or not settings.worker_password:
                    raise RuntimeError("缺少 DolphinDB worker 专用账号配置")
                failures = []
                for endpoint in settings.endpoints:
                    host, port = endpoint.rsplit(":", 1)
                    connection = dolphindb.session()
                    try:
                        message_logger = connection.msg_logger
                        message_logger.disable_stdout_sink()
                        if not any(sink.name == "loguru" for sink in message_logger.list_sinks()):
                            message_logger.add_sink(WorkerLogSink())
                        if not connection.connect(
                            host.strip("[]"), int(port),
                            settings.worker_username, settings.worker_password,
                            highAvailability=False, reconnect=False,
                        ):
                            raise ConnectionError("服务端未接受连接")
                    except BaseException as error:
                        try:
                            connection.close()
                        except Exception as close_error:
                            logger.warning(f"连接失败后关闭会话异常：{type(close_error).__name__}")
                        if not isinstance(error, Exception):
                            raise
                        # SDK认证异常可能包含凭据，仅记录端点和异常类型。
                        failures.append(f"{endpoint}：{type(error).__name__}")
                        logger.warning(f"Worker 连接失败：{endpoint}，异常={type(error).__name__}")
                    else:
                        connections.callback(connection.close)
                        session = connection
                        break
                if session is None:
                    raise ConnectionError(f"更新账号所有端点连接失败：{'；'.join(failures)}")

            try:
                workers = create_workers(names, arguments, session=session, settings=settings)
            except (TypeError, ValueError) as error:
                logger.exception("Worker 初始化失败，未开始执行")
                parser.error(str(error))

            if owns_session and "barra" in names:
                from query.execute.api import initialize_query

                initialize_query(session)
            mode = "dry-run" if arguments.dry_run else "写入"
            if arguments.overwrite and any(name != "barra" for name in names):
                logger.warning(
                    "CoreData已启用覆盖模式：忽略增量水位重新获取指定区间，同键追加覆盖"
                )
            logger.info(
                f"Worker 任务开始：模式={mode}，"
                f"任务={len(workers):,}，选择={list(names)}"
            )

            if "barra" in names and not arguments.dry_run:
                logger.warning("Barra始终按start/end分年独立重算，整段校验后替换并上传三表；--codes限制模型证券域，不是个股增补")
            started = time.perf_counter()
            total = 0
            result_name = "校验" if arguments.dry_run else "写入"
            for number, worker in enumerate(workers, start=1):
                logger.info(f"运行 Worker {number:,}/{len(workers):,}：{worker}")
                try:
                    rows = dry_run_worker(worker) if arguments.dry_run else worker.run()
                except KeyboardInterrupt:
                    total += 0 if arguments.dry_run else worker.partial_write_rows
                    logger.warning(
                        f"Worker 任务被用户中断：{worker}，"
                        f"已确认{result_name}={total:,}行，耗时={time.perf_counter() - started:.2f}秒"
                    )
                    return 130
                except Exception:
                    total += 0 if arguments.dry_run else worker.partial_write_rows
                    logger.exception(
                        f"Worker 任务失败并停止：{worker}，"
                        f"已确认{result_name}={total:,}行，"
                        f"后续未运行={len(workers) - number:,}，"
                        f"耗时={time.perf_counter() - started:.2f}秒"
                    )
                    return 1
                total += rows

            elapsed = time.perf_counter() - started
        logger.success(
            f"Worker 任务全部完成：{result_name}={total:,}行，"
            f"任务={len(workers):,}，耗时={elapsed:.2f}秒"
        )
        return 0
    except KeyboardInterrupt:
        logger.warning("Worker 连接或初始化被用户中断")
        return 130
    except Exception as error:
        logger.error(f"Worker 连接、初始化或关闭失败并停止：{type(error).__name__}")
        return 1


def main(
        argv: Sequence[str] | None = None,
        *,
        session: Any | None = None,
        settings: type[WorkerSettings] = WorkerSettings,
) -> int:
    """独立编译查询脚本或运行Worker，不依赖Scheme安装。"""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "workers":
        return run_workers(arguments[1:], prog="query workers", session=session, settings=settings)
    parser = argparse.ArgumentParser(prog="query", description="编译查询 DOS 或更新因子窄表。")
    commands = parser.add_subparsers(dest="command", required=True)
    compile_parser = commands.add_parser("compile", help="编译可直接运行的会话脚本，不连接数据库")
    compile_parser.add_argument("--output", type=Path, help="输出 DOS 文件；省略时输出到 stdout")
    commands.add_parser("workers", help="更新因子窄表，使用 workers --help 查看选项")
    parsed = parser.parse_args(arguments)
    from query.database.compile.script import build_script

    script = build_script()
    if parsed.output is None:
        print(script, end="")
    else:
        parsed.output.parent.mkdir(parents=True, exist_ok=True)
        parsed.output.write_text(script, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
