"""定义逐代码更新单个接口的抽象 Worker。"""

import time
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import timedelta
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
    get_codes,
    logger,
    normalize_date,
)

from .worker import BaseWorker


class StockWorker(BaseWorker, ABC):
    """按证券代码并发调用单个固定数据接口。"""

    @abstractmethod
    def __str__(self) -> str:
        """返回用于日志输出的按代码 Worker 标识。"""
        return "<StockWorker>"

    def __init__(
            self,
            codes: Sequence[str] | None = None,
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
        """初始化按代码更新范围、代码池、并发和写入配置。"""
        if codes is None:
            codes = get_codes()
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
        if isinstance(codes, (str, bytes)):
            raise TypeError("codes 必须是字符串序列")
        normalized_codes: list[str] = []
        seen_codes: set[str] = set()
        for code in codes:
            if not isinstance(code, str):
                raise TypeError("codes 必须全部是字符串")
            normalized_code = code.strip()
            if not normalized_code:
                raise ValueError("codes 不能包含空值")
            if normalized_code not in seen_codes:
                normalized_codes.append(normalized_code)
                seen_codes.add(normalized_code)
        if not normalized_codes:
            raise ValueError("codes 不能为空")
        self.codes = tuple(normalized_codes)
        logger.debug(
            f"{self} 初始化：代码={len(self.codes):,}，"
            f"{self.start_date:%Y-%m-%d} 至 {self.end_date:%Y-%m-%d}，"
            f"threads={self.threads}，throttle={self.throttle}，"
            f"max_retries={self.retry.max_retries}，"
            f"batch_size={self.batch_size}"
        )

    def get_last_dates(self) -> dict[str, pd.Timestamp]:
        """返回已有数据中每个代码的最近日期，无记录的代码不在字典中。"""
        started = time.perf_counter()
        logger.debug(
            f"{self} 查询 {len(self.codes):,} 个代码的最近数据日"
        )
        session = self.require_session()
        session.upload(
            {
                "stockWorkerCodes": np.asarray(self.codes, dtype=str),
                "stockWorkerLastDateFactors": np.asarray(self.factors, dtype=str),
            }
        )
        result = session.run(
            f"""
            select {CODE_COLUMN}, max({TIME_COLUMN}) as {TIME_COLUMN}
            from {core_table(self.settings)}
            where {CODE_COLUMN} in symbol(stockWorkerCodes)
              and {FACTOR_COLUMN} in symbol(stockWorkerLastDateFactors)
            group by {CODE_COLUMN}
            """
        )
        dates = (
            {
                str(getattr(row, CODE_COLUMN)): normalize_date(getattr(row, TIME_COLUMN), TIME_COLUMN)
                for row in result.itertuples(index=False)
                if not pd.isna(getattr(row, TIME_COLUMN))
            }
            if result is not None and not result.empty
            else {}
        )
        elapsed = time.perf_counter() - started
        date_range = (
            f"{min(dates.values()):%Y-%m-%d} 至 "
            f"{max(dates.values()):%Y-%m-%d}"
            if dates
            else "无"
        )
        covered_count = len(dates)
        missing_count = max(len(self.codes) - covered_count, 0)
        logger.info(
            f"{self} 增量基线：覆盖={covered_count:,}/{len(self.codes):,}，"
            f"缺失={missing_count:,}，最近数据日={date_range}，"
            f"因子={len(self.factors):,}，查询耗时={elapsed:.2f}秒"
        )
        return dates

    def melt(
            self,
            code: str,
            data: pd.DataFrame,
            *,
            start_date: pd.Timestamp,
            end_date: pd.Timestamp,
    ) -> pd.DataFrame:
        """把单个代码的接口宽表转换并规范为可直接写入的四列长表。"""
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"{self}[{code}] 返回值不是 DataFrame")
        if data.empty:
            return self.EMPTY
        required = {TIME_COLUMN, *self.factors}
        if missing := required - set(data.columns):
            raise ValueError(f"{self}[{code}] 返回结果缺少列：{sorted(missing)}")
        result = data.loc[:, [TIME_COLUMN, *self.factors]].copy()
        result[TIME_COLUMN] = pd.to_datetime(
            result[TIME_COLUMN],
            errors="coerce",
        )
        if result[TIME_COLUMN].isna().any():
            raise ValueError(f"{self}[{code}] 返回了无效 {TIME_COLUMN}")
        result = result[
            result[TIME_COLUMN].between(start_date, end_date)
        ]
        result[CODE_COLUMN] = code
        result = result.melt(
            id_vars=[TIME_COLUMN, CODE_COLUMN],
            value_vars=list(self.factors),
            var_name=FACTOR_COLUMN,
            value_name=VALUE_COLUMN,
        )
        return self.normalize_result(result)

    @abstractmethod
    def fetch_one(
            self,
            code: str,
            *,
            start_date: pd.Timestamp,
            end_date: pd.Timestamp,
    ) -> pd.DataFrame:
        """返回一个代码已规范的四列长表，空结果返回 ``self.EMPTY``。

        实现应把接口宽表交给 :meth:`melt` 并直接返回其结果，不得返回
        ``None``、接口原始宽表，或在 ``melt`` 之后再次清洗。
        所有外部请求必须通过 ``self.retry`` 或 ``self.paginator.fetch``
        发起，以共享统一的限流和重试配置。
        """
        raise NotImplementedError

    def fetch_all(self) -> Iterable[pd.DataFrame]:
        """按代码增量区间并发获取并生成可直接写入的四列长表。"""
        started = time.perf_counter()
        self.paginator.reset()
        last_dates = {} if self.overwrite else self.get_last_dates()
        end_date = self.end_date
        tasks: list[tuple[str, pd.Timestamp]] = []
        first_count = 0
        resumed_count = 0
        current_count = 0
        for code in self.codes:
            last_date = last_dates.get(code)
            start_date = (
                self.start_date
                if last_date is None
                else last_date + timedelta(days=1)
            )
            if start_date <= end_date:
                tasks.append((code, start_date))
                if last_date is None:
                    first_count += 1
                else:
                    resumed_count += 1
            else:
                current_count += 1

        start_range = (
            f"{min(task[1] for task in tasks):%Y-%m-%d} 至 "
            f"{max(task[1] for task in tasks):%Y-%m-%d}"
            if tasks
            else "无"
        )
        logger.info(
            f"{self} {'覆盖' if self.overwrite else '增量'}计划："
            f"首次={first_count:,}，续更={resumed_count:,}，"
            f"已最新={current_count:,}，"
            f"待请求={len(tasks):,}/{len(self.codes):,}，"
            f"实际起点={start_range}，截止={end_date:%Y-%m-%d}"
        )
        failure_count = 0
        rows = 0
        empty_count = 0
        nonempty_count = 0
        task_index = 0
        status = "进行中"
        executor = ThreadPoolExecutor(max_workers=self.threads)
        futures = {}
        try:
            while task_index < len(tasks) or futures:
                # 先检查已结束请求，不能在已知失败之前再补交后续代码。
                completed = {future for future in futures if future.done()}
                if not completed:
                    while task_index < len(tasks) and len(futures) < self.threads:
                        code, start_date = tasks[task_index]
                        future = executor.submit(
                            self.fetch_one,
                            code,
                            start_date=start_date,
                            end_date=end_date,
                        )
                        futures[future] = (code, start_date)
                        task_index += 1
                    completed = wait(futures, return_when=FIRST_COMPLETED)[0]

                ready: list[pd.DataFrame] = []
                for future in completed:
                    code, start_date = futures.pop(future)
                    try:
                        frame = self.check(future.result())
                    except Exception:
                        failure_count += 1
                        logger.exception(
                            f"{self}[{code}] 获取失败并停止，区间="
                            f"{start_date:%Y-%m-%d} 至 "
                            f"{end_date:%Y-%m-%d}，"
                            f"未提交={len(tasks) - task_index:,}"
                        )
                        raise
                    rows += len(frame)
                    empty_count += int(frame.empty)
                    nonempty_count += int(not frame.empty)
                    ready.append(frame)
                yield from ready
            status = "完成"
        except GeneratorExit:
            status = "中止"
            raise
        except BaseException:
            status = "失败"
            raise
        finally:
            # 取消排队任务，不等待其它在途请求；已开始的请求不能由线程池强制中断。
            executor.shutdown(wait=status == "完成", cancel_futures=True)
            elapsed = time.perf_counter() - started
            logger.info(
                f"{self} 获取汇总：状态={status}，"
                f"任务={len(tasks):,}，非空={nonempty_count:,}，"
                f"空={empty_count:,}，结果行={rows:,}，"
                f"失败={failure_count:,}{self.paginator.summary()}，"
                f"耗时={elapsed:.2f}秒"
            )
