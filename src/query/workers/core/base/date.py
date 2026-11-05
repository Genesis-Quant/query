"""定义逐自然日更新的抽象 Worker。"""
import time
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any

import numpy as np
import pandas as pd

from query.config import DATA_START_DATE, DolphinSettings
from query.database.tables.core import core_table
from query.utils import (
    CODE_COLUMN,
    FACTOR_COLUMN,
    TIME_COLUMN,
    VALUE_COLUMN,
    DateLike,
    logger,
    normalize_date,
)

from .worker import BaseWorker


class DateWorker(BaseWorker, ABC):
    """从数据库最近数据日的下一自然日开始逐日调用具体接口。"""

    @abstractmethod
    def __str__(self) -> str:
        """返回用于日志输出的逐日 Worker 标识。"""
        return "<DateWorker>"

    def __init__(
            self,
            chunk_size: int = 50,
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
        """初始化逐日更新范围、并发配置和分块大小。"""
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        self.chunk_size = chunk_size
        super().__init__(
            session=session,
            settings=settings,
            start_date=start_date,
            end_date=end_date,
            threads=threads,
            throttle=throttle,
            max_retries=max_retries,
            retry_interval=retry_interval,
            batch_size=batch_size,
            overwrite=overwrite,
        )
        logger.debug(
            f"{self} 初始化："
            f"{self.start_date:%Y-%m-%d} 至 {self.end_date:%Y-%m-%d}，"
            f"threads={self.threads}，throttle={self.throttle}，"
            f"max_retries={self.retry.max_retries}，"
            f"chunk_size={self.chunk_size}，"
            f"batch_size={self.batch_size}"
        )

    def melt(
            self,
            current_date: pd.Timestamp,
            data: pd.DataFrame,
    ) -> pd.DataFrame:
        """把单日接口宽表转换并规范为可直接写入的四列长表。"""
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                f"{self}[{current_date:%Y-%m-%d}] "
                "返回值不是 DataFrame"
            )
        if data.empty:
            return self.EMPTY
        required = {TIME_COLUMN, CODE_COLUMN, *self.factors}
        if missing := required - set(data.columns):
            raise ValueError(
                f"{self}[{current_date:%Y-%m-%d}] "
                f"返回结果缺少列：{sorted(missing)}"
            )
        result = data.loc[
            :,
            [TIME_COLUMN, CODE_COLUMN, *self.factors],
        ].copy()
        result[TIME_COLUMN] = pd.to_datetime(
            result[TIME_COLUMN],
            errors="coerce",
        )
        if result[TIME_COLUMN].isna().any():
            raise ValueError(
                f"{self}[{current_date:%Y-%m-%d}] "
                f"返回了无效 {TIME_COLUMN}"
            )
        result = result[
            result[TIME_COLUMN].dt.normalize().eq(current_date)
        ]
        result = result.melt(
            id_vars=[TIME_COLUMN, CODE_COLUMN],
            value_vars=list(self.factors),
            var_name=FACTOR_COLUMN,
            value_name=VALUE_COLUMN,
        )
        return self.normalize_result(result)

    @property
    def incremental_scope_codes(self) -> Sequence[str] | None:
        """返回增量基线查询需要限制的代码范围。"""
        return None

    def pending_dates(self) -> pd.DatetimeIndex:
        """返回最近完整数据日起到截止日期之间的全部自然日。"""
        last_date = None if self.overwrite else self.get_last_date()
        start_date = (
            self.start_date
            if last_date is None
            else max(
                self.start_date,
                normalize_date(last_date, "last_date"),
            )
        )
        end_date = self.end_date

        if start_date > end_date:
            logger.info(
                f"{self} 更新计划：无需更新，"
                f"实际起始日={start_date:%Y-%m-%d}，"
                f"结束日={end_date:%Y-%m-%d}，自然日=0，chunk=0"
            )
            return pd.DatetimeIndex([])

        dates = pd.date_range(start_date, end_date, freq="D")
        chunk_count = (len(dates) + self.chunk_size - 1) // self.chunk_size
        if self.overwrite:
            mode = "覆盖"
        elif last_date is None:
            mode = "全量"
        else:
            mode = "增量"
        logger.info(
            f"{self} 更新计划：模式={mode}，"
            f"实际区间={dates[0]:%Y-%m-%d} 至 {dates[-1]:%Y-%m-%d}，"
            f"自然日={len(dates):,}，chunk={chunk_count:,}"
        )
        return dates

    def get_last_date(self) -> pd.Timestamp | None:
        """返回当前 Worker 全部因子均有数据的最近自然日。

        增量计划会从该日重新抓取，避免上一次分批写入中断时把只写入
        部分数据的最后一天误认为已经完成。
        """
        started = time.perf_counter()
        logger.debug(f"{self} 查询最近数据日")
        session = self.require_session()
        upload_values = {
            "dateWorkerFactors": np.asarray(self.factors, dtype=str),
        }
        scope_codes = self.incremental_scope_codes
        scope_clause = ""
        if scope_codes is not None:
            normalized_codes = tuple(
                dict.fromkeys(
                    str(code).strip()
                    for code in scope_codes
                    if str(code).strip()
                )
            )
            if not normalized_codes:
                raise RuntimeError(f"{self} 增量基线代码范围为空")
            upload_values["dateWorkerCodes"] = np.asarray(normalized_codes, dtype=str)
            scope_clause = f"and {CODE_COLUMN} in symbol(dateWorkerCodes)"
        session.upload(upload_values)
        result = session.run(
            f"""
            select {FACTOR_COLUMN}, max({TIME_COLUMN}) as {TIME_COLUMN}
            from {core_table(self.settings)}
            where {FACTOR_COLUMN} in symbol(dateWorkerFactors)
              {scope_clause}
            group by {FACTOR_COLUMN}
            """
        )
        required_columns = {FACTOR_COLUMN, TIME_COLUMN}
        if (
                result is None
                or result.empty
                or not required_columns.issubset(result.columns)
        ):
            elapsed = time.perf_counter() - started
            logger.info(
                f"{self} 增量基线：因子={len(self.factors):,}，"
                f"最近数据日=无，查询耗时={elapsed:.2f}秒"
            )
            return None

        factor_dates = {
            str(row[FACTOR_COLUMN]): normalize_date(
                row[TIME_COLUMN],
                TIME_COLUMN,
            )
            for _, row in result.iterrows()
            if not pd.isna(row[TIME_COLUMN])
        }
        missing_factors = set(self.factors) - factor_dates.keys()
        if missing_factors:
            elapsed = time.perf_counter() - started
            logger.info(
                f"{self} 增量基线：因子={len(self.factors):,}，"
                f"缺失因子={sorted(missing_factors)}，最近完整数据日=无，"
                f"查询耗时={elapsed:.2f}秒"
            )
            return None

        latest = min(factor_dates.values())
        elapsed = time.perf_counter() - started
        scope_text = (
            f"，代码范围={len(normalized_codes):,}"
            if scope_codes is not None
            else ""
        )
        logger.info(
            f"{self} 增量基线：因子={len(self.factors):,}，"
            f"最近完整数据日={latest:%Y-%m-%d}{scope_text}，"
            "将重放该自然日，"
            f"查询耗时={elapsed:.2f}秒"
        )
        return latest

    @abstractmethod
    def fetch_one(self, current_date: pd.Timestamp) -> pd.DataFrame:
        """返回一个自然日已规范的四列长表，空结果返回 ``self.EMPTY``。

        实现应把接口宽表交给 :meth:`melt` 并直接返回其结果，不得返回
        ``None``、接口原始宽表，或在 ``melt`` 之后再次清洗。
        所有外部请求必须通过 ``self.retry`` 或 ``self.paginator.fetch``
        发起，以共享统一的限流和重试配置。
        """
        raise NotImplementedError

    def fetch_all(self) -> Iterable[pd.DataFrame]:
        """按块并发获取，按日期顺序生成可直接写入的完整 chunk。"""
        started = time.perf_counter()
        self.paginator.reset()
        dates = self.pending_dates()
        chunk_count = (len(dates) + self.chunk_size - 1) // self.chunk_size
        rows, nonempty_count, empty_count, failed_count = 0, 0, 0, 0

        if dates.empty:
            elapsed = time.perf_counter() - started
            logger.info(
                f"{self} 获取汇总：状态=完成，"
                f"日期=0/0，非空=0，空=0，"
                f"结果行=0，失败=0，耗时={elapsed:.2f}秒"
            )
            return

        # 一个线程池覆盖全部 chunk，避免每十天反复创建和销毁线程。
        status = "进行中"
        executor = ThreadPoolExecutor(max_workers=self.threads)
        try:
            for offset in range(0, len(dates), self.chunk_size):
                chunk = dates[offset:offset + self.chunk_size]
                chunk_number = offset // self.chunk_size + 1
                frames: dict[pd.Timestamp, pd.DataFrame] = {}
                logger.debug(
                    f"{self} 获取 chunk {chunk_number}/"
                    f"{chunk_count}：{chunk[0]:%Y-%m-%d} 至 "
                    f"{chunk[-1]:%Y-%m-%d}"
                )

                futures = {}
                date_index = 0
                # 最多只提交 threads 个日期，不能让失败后排队的整块日期继续请求。
                while date_index < len(chunk) or futures:
                    completed = {future for future in futures if future.done()}
                    if not completed:
                        while date_index < len(chunk) and len(futures) < self.threads:
                            date_value = chunk[date_index]
                            futures[executor.submit(self.fetch_one, date_value)] = date_value
                            date_index += 1
                        completed = wait(futures, return_when=FIRST_COMPLETED)[0]
                    for future in completed:
                        date_value = futures.pop(future)
                        try:
                            frame = self.check(future.result())
                            frames[date_value] = frame
                        except Exception:
                            failed_count += 1
                            logger.exception(
                                f"{self}[{date_value:%Y-%m-%d}] 获取失败并停止，"
                                f"chunk={chunk[0]:%Y-%m-%d} 至 "
                                f"{chunk[-1]:%Y-%m-%d}，后续 chunk 不再运行"
                            )
                            raise
                        rows += len(frame)
                        nonempty_count += int(not frame.empty)
                        empty_count += int(frame.empty)

                data = [
                    frames[date]
                    for date in chunk
                    if not frames[date].empty
                ]
                result = (
                    pd.concat(data, ignore_index=True)
                    if data
                    else self.EMPTY
                )
                # fetch_one 已规范每个结果；拼接后不再二次清洗或排序。
                logger.debug(
                    f"{self} chunk {chunk_number}/"
                    f"{chunk_count} 获取完成，共 {len(result):,} 行"
                )
                yield result
            status = "完成"
        except GeneratorExit:
            status = "中止"
            raise
        except BaseException:
            status = "失败"
            raise
        finally:
            executor.shutdown(wait=status == "完成", cancel_futures=True)
            elapsed = time.perf_counter() - started
            completed_count = nonempty_count + empty_count + failed_count
            logger.info(
                f"{self} 获取汇总：状态={status}，"
                f"日期={completed_count:,}/{len(dates):,}，"
                f"非空={nonempty_count:,}，空={empty_count:,}，"
                f"结果行={rows:,}，失败={failed_count:,}"
                f"{self.paginator.summary()}，耗时={elapsed:.2f}秒"
            )

    def run(self) -> int:
        """按时间顺序写入完整 chunk，并返回实际写入总行数。"""
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
            f"因子={len(self.factors):,}，线程={self.threads:,}，"
            f"限速={throttle_text}，"
            f"chunk={self.chunk_size:,}天，批量={self.batch_size:,}行"
        )
        total = 0
        try:
            with self.create_writer() as writer:
                for data in self.fetch_all():
                    if not data.empty:
                        total += self.write(writer, data)
        except BaseException:
            total = self.partial_write_rows
            elapsed = time.perf_counter() - started
            logger.exception(
                f"{name} 更新失败：已确认写入={total:,}行，"
                f"耗时={elapsed:.2f}秒"
            )
            raise

        elapsed = time.perf_counter() - started
        throughput = total / elapsed if elapsed else 0.0
        logger.success(
            f"{name} 更新完成：写入={total:,}行，"
            f"耗时={elapsed:.2f}秒，吞吐={throughput:,.0f}行/秒"
        )
        return total
