"""定义所有数据更新 Worker 的统一入口和写入流程。"""

import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping
from threading import Lock
from typing import Any, ClassVar

import numpy as np
import pandas as pd

from query.config import DATA_START_DATE, DolphinSettings
from query.database import CoreTableWriter
from query.utils import (
    CODE_COLUMN,
    CORE_COLUMNS,
    FACTOR_COLUMN,
    TIME_COLUMN,
    VALUE_COLUMN,
    DateLike,
    RateLimiter,
    Retry,
    logger,
    normalize_date_range,
)


class Paginator:
    """通过 ``limit/offset`` 完整获取 DataFrame 并累计分页统计。"""

    def __init__(self, retry: Retry) -> None:
        self.retry = retry
        self.lock = Lock()
        self.stats: dict[str, int] = {}
        self.reset()

    def reset(self) -> None:
        """清空当前一轮更新的分页汇总计数。"""
        with self.lock:
            self.stats = {
                "calls": 0,
                "requests": 0,
                "pages": 0,
                "multi_page": 0,
                "rows": 0,
                "extra_rows": 0,
            }

    def record(
            self,
            *,
            request_count: int,
            page_count: int,
            row_count: int,
            extra_rows: int,
    ) -> None:
        """累计一次分页查询。"""
        with self.lock:
            self.stats["calls"] += 1
            self.stats["requests"] += request_count
            self.stats["pages"] += page_count
            self.stats["rows"] += row_count
            self.stats["extra_rows"] += extra_rows
            self.stats["multi_page"] += int(page_count > 1)

    def summary(self) -> str:
        """返回适合追加到 Worker 汇总日志的分页信息。"""
        with self.lock:
            stats = dict(self.stats)
        if not stats["calls"]:
            return ""
        return (
            f"，分页完成={stats['calls']:,}，"
            f"多页={stats['multi_page']:,}，"
            f"请求={stats['requests']:,}，"
            f"有效页={stats['pages']:,}，"
            f"返回行={stats['rows']:,}，"
            f"补齐行={stats['extra_rows']:,}"
        )

    def fetch(
            self,
            endpoint: Callable[..., pd.DataFrame | None],
            *,
            params: Mapping[str, object],
            page_size: int,
            context: str,
            stop_on_short: bool = False,
            max_pages: int = 10_000,
    ) -> pd.DataFrame:
        """分页获取完整响应，所有页面原样合并，不执行清洗或去重。"""
        if page_size <= 0:
            raise ValueError("page_size 必须大于 0")
        if max_pages <= 0:
            raise ValueError("max_pages 必须大于 0")

        request_params = dict(params)
        if {"limit", "offset"} & request_params.keys():
            raise ValueError("params 不能包含 limit 或 offset")

        pages: list[pd.DataFrame] = []
        expected_columns: tuple[object, ...] | None = None
        seen_pages: set[tuple[tuple[object, ...], bytes]] = set()
        empty_result: pd.DataFrame | None = None
        started = time.perf_counter()
        request_count = 0
        stop_reason: str
        offset = 0

        for page_number in range(1, max_pages + 1):
            current_offset = offset

            def request_page() -> pd.DataFrame:
                nonlocal request_count
                request_count += 1
                response = endpoint(
                    **request_params,
                    limit=page_size,
                    offset=current_offset,
                )
                if not isinstance(response, pd.DataFrame):
                    raise TypeError(
                        f"{context} 分页响应不是 DataFrame："
                        f"{type(response).__name__}"
                    )
                return response

            page = self.retry(
                request_page,
                context=(
                    f"{context} 第 {page_number} 页"
                    f"[offset={current_offset}, limit={page_size}]"
                ),
            )

            if page.empty:
                empty_result = page
                stop_reason = "空页"
                break

            page = page.reset_index(drop=True)
            columns = tuple(page.columns)
            if expected_columns is None:
                expected_columns = columns
            elif columns != expected_columns:
                raise ValueError(
                    f"{context} 第 {page_number} 页字段发生变化："
                    f"{list(columns)} != {list(expected_columns)}"
                )

            hashes = pd.util.hash_pandas_object(page, index=False).to_numpy()
            signature = (columns, np.sort(hashes).tobytes())
            if signature in seen_pages:
                raise RuntimeError(
                    f"{context} 第 {page_number} 页内容重复，offset 可能未生效"
                )
            seen_pages.add(signature)

            pages.append(page)
            offset += len(page)
            if stop_on_short and len(page) < page_size:
                stop_reason = "短页"
                break
        else:
            raise RuntimeError(
                f"{context} 已达到最大分页数 {max_pages:,}，结果可能仍未完整"
            )

        if pages:
            all_null_columns = [
                column
                for column in expected_columns or ()
                if all(page[column].isna().all() for page in pages)
            ]
            concat_pages = [page.dropna(axis="columns", how="all") for page in pages]
            result = pd.concat(concat_pages, ignore_index=True)
            for column in all_null_columns:
                result[column] = pd.concat(
                    [page[column] for page in pages],
                    ignore_index=True,
                )
            result = result.reindex(columns=expected_columns)
        elif empty_result is not None:
            result = empty_result
        else:
            result = pd.DataFrame()
        page_count = len(pages)
        total_rows = sum(map(len, pages))
        first_page_rows = len(pages[0]) if pages else 0
        extra_rows = total_rows - first_page_rows
        self.record(
            request_count=request_count,
            page_count=page_count,
            row_count=total_rows,
            extra_rows=extra_rows,
        )
        if request_count > 1:
            elapsed = time.perf_counter() - started
            message = (
                f"{context} 分页完成：请求={request_count:,}，"
                f"有效页={page_count:,}，原始行={total_rows:,}，"
                f"补齐行={extra_rows:,}，"
                f"停止={stop_reason or '未知'}，耗时={elapsed:.2f}秒"
            )
            if page_count > 1:
                logger.info(message)
            else:
                logger.debug(message)
        return result


class BaseWorker(ABC):
    """统一管理运行配置、返回格式、失败重试和批量写入。"""

    COLUMNS: ClassVar[tuple[str, ...]] = CORE_COLUMNS
    EMPTY: ClassVar[pd.DataFrame] = pd.DataFrame(
        {
            TIME_COLUMN: pd.Series(dtype="datetime64[ns]"),
            CODE_COLUMN: pd.Series(dtype="object"),
            FACTOR_COLUMN: pd.Series(dtype="object"),
            VALUE_COLUMN: pd.Series(dtype="float64"),
        }
    )

    @abstractmethod
    def __str__(self) -> str:
        """返回用于日志输出的 Worker 标识。"""
        return "<BaseWorker>"

    def __init__(
            self,
            *,
            session: Any | None = None,
            settings: type[DolphinSettings] = DolphinSettings,
            start_date: DateLike = DATA_START_DATE,
            end_date: DateLike | None = None,
            threads: int = 3,
            throttle: int = 8,
            max_retries: int = 3,
            retry_interval: float = 1.0,
            batch_size: int = 800_000,
            overwrite: bool = False,
    ) -> None:
        """初始化所有 Worker 共享的日期、并发和写入配置。"""
        fields = self.fields
        if not fields or len(fields) != len(set(fields)):
            raise TypeError(f"{self}.fields 定义无效")
        if threads <= 0:
            raise ValueError("threads 必须大于 0")
        if batch_size <= 0:
            raise ValueError("batch_size 必须大于 0")
        if not isinstance(overwrite, bool):
            raise TypeError("overwrite 必须是 bool")

        end_date = pd.Timestamp.today() if end_date is None else end_date
        self.start_date, self.end_date = normalize_date_range(
            start_date,
            end_date,
        )
        self.session = session
        self.settings = settings
        self.threads = threads
        self.batch_size = batch_size
        self.overwrite = overwrite
        self.retry = Retry(
            max_retries=max_retries,
            retry_interval=retry_interval,
            limiter=RateLimiter(throttle),
        )
        self.paginator = Paginator(self.retry)
        # 累计本轮已确认提交的行数，失败或中断时供 CLI 汇总；仅在 run() 开始时重置。
        self.partial_write_rows = 0

    @property
    def throttle(self) -> int:
        """返回当前限流器实际使用的每秒请求数。"""
        return self.limiter.rate_per_second

    @property
    def limiter(self) -> RateLimiter:
        """返回当前重试器实际使用的限流器。"""
        return self.retry.limiter

    @limiter.setter
    def limiter(self, limiter: RateLimiter) -> None:
        """同步替换当前重试器使用的限流器。"""
        self.retry.limiter = limiter

    @property
    def factors(self) -> tuple[str, ...]:
        """返回当前 Worker 写入的全部固定因子。"""
        raise NotImplementedError(f"{self} 不写入统一因子表")

    @property
    def fields(self) -> tuple[str, ...]:
        """返回当前 Worker 持久化的数据字段。"""
        return self.factors

    @abstractmethod
    def fetch_all(self) -> Iterable[pd.DataFrame]:
        """生成已符合四列返回约定、可直接写入的增量数据。"""
        raise NotImplementedError

    def normalize_result(self, data: pd.DataFrame) -> pd.DataFrame:
        """完成 ``fetch_one`` 返回前唯一一次行级规范化。

        返回值严格包含 ``time/code/factor/value`` 四列；``time`` 为
        datetime64，``code`` 和 ``factor`` 为非空字符串，``value`` 为有限
        float。空值和无穷值仅从 ``value`` 中删除，重复键保留最后一条。

        该方法只能由 ``melt`` 调用。``fetch_all``、``write`` 和数据库写入器
        均把返回值视为成品，不再转换类型、清理空值、去重或排序。
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("待规范数据必须是 DataFrame")
        if missing := set(self.COLUMNS) - set(data.columns):
            raise ValueError(f"待规范数据缺少列：{sorted(missing)}")
        if data.empty:
            return self.EMPTY

        result = data.loc[:, list(self.COLUMNS)].copy()
        if not pd.api.types.is_datetime64_any_dtype(result[TIME_COLUMN]):
            raise ValueError(f"{TIME_COLUMN} 列必须为 datetime64 类型")

        codes = result[CODE_COLUMN].astype("string").str.strip()
        factors = result[FACTOR_COLUMN].astype("string").str.strip()
        invalid_keys = result[TIME_COLUMN].isna()
        invalid_keys |= codes.isna() | codes.eq("")
        invalid_keys |= factors.isna() | factors.eq("")
        if invalid_keys.any():
            raise ValueError(
                f"待规范数据包含 {int(invalid_keys.sum())} 行无效 "
                f"{'/'.join(CORE_COLUMNS[:3])}"
            )

        values = pd.to_numeric(result[VALUE_COLUMN], errors="coerce")
        result[CODE_COLUMN] = codes.astype(object)
        result[FACTOR_COLUMN] = factors.astype(object)
        result[VALUE_COLUMN] = values.to_numpy(dtype=float, na_value=np.nan)
        result.loc[~np.isfinite(result[VALUE_COLUMN]), VALUE_COLUMN] = np.nan

        result = (
            result.dropna(subset=[VALUE_COLUMN])
            .drop_duplicates(list(CORE_COLUMNS[:3]), keep="last")
            .sort_values([FACTOR_COLUMN, CODE_COLUMN, TIME_COLUMN])
            .reset_index(drop=True)
        )
        return self.EMPTY if result.empty else result

    def check(self, data: pd.DataFrame) -> pd.DataFrame:
        """校验 ``fetch_one`` 的结构契约，并原样返回 DataFrame。

        本方法只检查列和 dtype，不修改数据。内容清洗必须已经由
        :meth:`normalize_result` 完成，调用方可直接使用本方法的返回值。
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("fetch_one 结果必须是 DataFrame")
        if tuple(data.columns) != self.COLUMNS:
            raise ValueError(
                "fetch_one 结果列必须严格为 "
                f"{list(self.COLUMNS)}，实际为 {list(data.columns)}"
            )
        if not pd.api.types.is_datetime64_any_dtype(data[TIME_COLUMN]):
            raise ValueError(
                f"fetch_one 结果的 {TIME_COLUMN} 列必须为 datetime64 类型"
            )
        if not pd.api.types.is_float_dtype(data[VALUE_COLUMN]):
            raise ValueError(
                f"fetch_one 结果的 {VALUE_COLUMN} 列必须为 float 类型"
            )
        return data

    def require_session(self) -> Any:
        """读写数据库前要求调用方提供会话，不创建或关闭连接。"""
        if self.session is None:
            raise TypeError(f"{self} 需要调用方传入已有的 session")
        return self.session

    def create_writer(self) -> Any:
        """使用已有会话创建写入器。"""
        return CoreTableWriter(
            self.factors,
            session=self.require_session(),
            settings=self.settings,
        )

    def write(self, writer: Any, data: pd.DataFrame) -> int:
        """切分已规范长表并写入，返回 DolphinDB 实际写入行数。"""
        total = 0
        batch_count = (len(data) + self.batch_size - 1) // self.batch_size
        # fetch_all 已保证返回契约；此处只控制网络批次，不再处理内容。
        for batch_number, offset in enumerate(
                range(0, len(data), self.batch_size),
                start=1,
        ):
            batch = data.iloc[offset:offset + self.batch_size]
            written = writer.append(batch)
            total += written
            self.partial_write_rows += written
            logger.debug(
                f"{self} 写入批次 {batch_number:,}/{batch_count:,}："
                f"提交={len(batch):,}行，实际写入={written:,}行，"
                f"本次累计={total:,}行"
            )
        return total

    def run(self) -> int:
        """执行完整增量更新并返回成功写入 DolphinDB 的总行数。"""
        name = str(self)
        started = time.perf_counter()
        self.partial_write_rows = 0
        throttle_text = (
            "不限速"
            if self.throttle == 0
            else f"{self.throttle:,}次/秒"
        )
        logger.info(
            f"{name} 开始更新："
            f"{self.start_date:%Y-%m-%d} 至 {self.end_date:%Y-%m-%d}，"
            f"字段={len(self.fields):,}，线程={self.threads:,}，"
            f"限速={throttle_text}，批量={self.batch_size:,}行"
        )
        batch: list[pd.DataFrame] = []
        rows, total = 0, 0
        try:
            with self.create_writer() as writer:
                for frame in self.fetch_all():
                    if frame.empty:
                        continue

                    # 这里只合并小结果以减少写入次数，不重复规范化。
                    batch.append(frame)
                    rows += len(frame)

                    if rows < self.batch_size:
                        continue

                    total += self.write(
                        writer,
                        pd.concat(batch, ignore_index=True),
                    )
                    batch.clear()
                    rows = 0

                if batch:
                    total += self.write(
                        writer,
                        pd.concat(batch, ignore_index=True),
                    )
        except BaseException:
            total = self.partial_write_rows
            elapsed = time.perf_counter() - started
            logger.exception(
                f"{name} 更新失败：已确认写入={total:,}行，"
                f"当前缓冲={rows:,}行，耗时={elapsed:.2f}秒"
            )
            raise

        elapsed = time.perf_counter() - started
        throughput = total / elapsed if elapsed > 0 else 0.0
        logger.success(
            f"{name} 更新完成：写入={total:,}行，耗时={elapsed:.2f}秒，"
            f"吞吐={throughput:,.0f}行/秒"
        )
        return total

    def __repr__(self) -> str:
        """返回与日志标识一致的调试字符串。"""
        return str(self)
