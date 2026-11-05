"""按申万行业有效区间维护动态行业枚举。"""

from __future__ import annotations

import re
import time
from collections.abc import Iterable
from enum import IntEnum

import numpy as np
import pandas as pd

from query.database.tables.core import core_table
from query.utils import (
    CODE_COLUMN,
    FACTOR_COLUMN,
    TIME_COLUMN,
    VALUE_COLUMN,
    logger,
    normalize_date,
)
from query.utils.ts_api import get_pro

from .base import BaseWorker

INDUSTRY_FACTORS = (
    "industry_l0",
    "industry_l1",
    "industry_l2",
    "industry_l3",
)


class IndustryLevel0(IntEnum):
    """现有系统使用的 11 类行业枚举；0 表示未知。"""

    UNKNOWN = 0
    ENERGY = 1
    MATERIALS = 2
    INDUSTRIALS = 3
    CONSUMER_DISCRETIONARY = 4
    CONSUMER_STAPLES = 5
    HEALTH_CARE = 6
    FINANCIALS = 7
    INFORMATION_TECHNOLOGY = 8
    TELECOM_SERVICES = 9
    UTILITIES = 10
    REAL_ESTATE = 11


INDUSTRY_LEVEL0_LABELS = {
    IndustryLevel0.UNKNOWN: "未知",
    IndustryLevel0.ENERGY: "能源",
    IndustryLevel0.MATERIALS: "材料",
    IndustryLevel0.INDUSTRIALS: "工业",
    IndustryLevel0.CONSUMER_DISCRETIONARY: "可选消费",
    IndustryLevel0.CONSUMER_STAPLES: "日常消费",
    IndustryLevel0.HEALTH_CARE: "医疗保健",
    IndustryLevel0.FINANCIALS: "金融",
    IndustryLevel0.INFORMATION_TECHNOLOGY: "信息技术",
    IndustryLevel0.TELECOM_SERVICES: "电信服务",
    IndustryLevel0.UTILITIES: "公用事业",
    IndustryLevel0.REAL_ESTATE: "房地产",
}

# 申万 2021 一级行业到现有 11 类行业的项目口径映射。
SW_LEVEL1_TO_LEVEL0 = {
    "801010.SI": IndustryLevel0.CONSUMER_STAPLES,
    "801030.SI": IndustryLevel0.MATERIALS,
    "801040.SI": IndustryLevel0.MATERIALS,
    "801050.SI": IndustryLevel0.MATERIALS,
    "801080.SI": IndustryLevel0.INFORMATION_TECHNOLOGY,
    "801110.SI": IndustryLevel0.CONSUMER_DISCRETIONARY,
    "801120.SI": IndustryLevel0.CONSUMER_STAPLES,
    "801130.SI": IndustryLevel0.CONSUMER_DISCRETIONARY,
    "801140.SI": IndustryLevel0.CONSUMER_DISCRETIONARY,
    "801150.SI": IndustryLevel0.HEALTH_CARE,
    "801160.SI": IndustryLevel0.UTILITIES,
    "801170.SI": IndustryLevel0.INDUSTRIALS,
    "801180.SI": IndustryLevel0.REAL_ESTATE,
    "801200.SI": IndustryLevel0.CONSUMER_DISCRETIONARY,
    "801210.SI": IndustryLevel0.CONSUMER_DISCRETIONARY,
    "801230.SI": IndustryLevel0.INDUSTRIALS,
    "801710.SI": IndustryLevel0.MATERIALS,
    "801720.SI": IndustryLevel0.INDUSTRIALS,
    "801730.SI": IndustryLevel0.INDUSTRIALS,
    "801740.SI": IndustryLevel0.INDUSTRIALS,
    "801750.SI": IndustryLevel0.INFORMATION_TECHNOLOGY,
    "801760.SI": IndustryLevel0.CONSUMER_DISCRETIONARY,
    "801770.SI": IndustryLevel0.TELECOM_SERVICES,
    "801780.SI": IndustryLevel0.FINANCIALS,
    "801790.SI": IndustryLevel0.FINANCIALS,
    "801880.SI": IndustryLevel0.CONSUMER_DISCRETIONARY,
    "801890.SI": IndustryLevel0.INDUSTRIALS,
    "801950.SI": IndustryLevel0.ENERGY,
    "801960.SI": IndustryLevel0.ENERGY,
    "801970.SI": IndustryLevel0.INDUSTRIALS,
    "801980.SI": IndustryLevel0.CONSUMER_STAPLES,
}

_INDUSTRY_CODE_PATTERN = re.compile(r"^(\d{6})\.SI$")
_MEMBER_FIELDS = (
    "ts_code,l1_code,l1_name,l2_code,l2_name,l3_code,l3_name,"
    "in_date,out_date,is_new"
)


def industry_enum_value(value: object, level: int) -> int:
    """将申万行业代码转换成可稳定写入 DOUBLE 的整数枚举。"""
    code = str(value).strip().upper()
    match = _INDUSTRY_CODE_PATTERN.fullmatch(code)
    if match is None:
        raise ValueError(f"申万 {level} 级行业代码无效：{value!r}")
    return int(match.group(1))


class IndustryWorker(BaseWorker):
    """抓取全部申万行业区间并写入可前向填充的变更事件。"""

    PAGE_SIZE = 2_000

    def __str__(self) -> str:
        """返回 Worker 日志标识。"""
        return "<IndustryWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        """返回自定义 11 类及申万一至三级行业因子。"""
        return INDUSTRY_FACTORS

    def get_last_date(self) -> pd.Timestamp | None:
        """从 coreData 读取四个行业因子的最近完整事件日期。"""
        started = time.perf_counter()
        session = self.require_session()
        session.upload({
            "industryWorkerFactors": np.asarray(self.factors, dtype=str)
        })
        result = session.run(f"""
            select {FACTOR_COLUMN}, max({TIME_COLUMN}) as {TIME_COLUMN}
            from {core_table(self.settings)}
            where {FACTOR_COLUMN} in symbol(industryWorkerFactors)
            group by {FACTOR_COLUMN}
        """)

        factor_dates = (
            {
                str(row[FACTOR_COLUMN]): normalize_date(
                    row[TIME_COLUMN],
                    TIME_COLUMN,
                )
                for _, row in result.iterrows()
                if not pd.isna(row[TIME_COLUMN])
            }
            if result is not None and not result.empty
            else {}
        )
        missing = set(self.factors) - factor_dates.keys()
        last_date = None if missing else min(factor_dates.values())
        elapsed = time.perf_counter() - started
        logger.info(
            f"{self} 增量基线：最近完整事件日="
            f"{last_date.strftime('%Y-%m-%d') if last_date is not None else '无'}，"
            f"缺失因子={sorted(missing)}，查询耗时={elapsed:.2f}秒"
        )
        return last_date

    def fetch_memberships(self) -> pd.DataFrame:
        """分页获取当前和历史申万行业成员区间。"""
        frames: list[pd.DataFrame] = []
        for is_new in ("Y", "N"):
            frame = self.paginator.fetch(
                get_pro().index_member_all,
                params={
                    "is_new": is_new,
                    "fields": _MEMBER_FIELDS,
                },
                page_size=self.PAGE_SIZE,
                context=f"{self}[is_new={is_new}]",
                stop_on_short=True,
            )
            if not frame.empty:
                frames.append(frame)
        if not frames:
            raise RuntimeError("index_member_all 没有返回任何行业成员")
        return pd.concat(frames, ignore_index=True)

    def transform_memberships(self, memberships: pd.DataFrame) -> pd.DataFrame:
        """把行业有效区间转换为初始快照、变更和失效事件。"""
        required = {
            "ts_code",
            "l1_code",
            "l2_code",
            "l3_code",
            "in_date",
            "out_date",
            "is_new",
        }
        if missing := required - set(memberships.columns):
            raise ValueError(
                f"index_member_all 返回结果缺少列：{sorted(missing)}"
            )
        if memberships.empty:
            return self.EMPTY

        data = memberships.loc[:, sorted(required)].copy()
        for column in ("ts_code", "l1_code", "l2_code", "l3_code"):
            data[column] = (
                data[column].astype("string").str.strip().str.upper()
            )
        if data[["ts_code", "l1_code", "l2_code", "l3_code"]].isna().any().any():
            raise ValueError("index_member_all 返回了空股票或行业代码")
        if data["ts_code"].eq("").any():
            raise ValueError("index_member_all 返回了空股票代码")

        raw_in_dates = data["in_date"].astype("string").str.strip()
        raw_out_dates = data["out_date"].astype("string").str.strip()
        in_dates = pd.to_datetime(
            raw_in_dates,
            format="%Y%m%d",
            errors="coerce",
        ).astype("datetime64[ns]")
        out_dates = pd.to_datetime(
            raw_out_dates.where(raw_out_dates.ne("")),
            format="%Y%m%d",
            errors="coerce",
        ).astype("datetime64[ns]")
        if in_dates.isna().any():
            invalid = data.loc[in_dates.isna(), "in_date"].head(10).tolist()
            raise ValueError(f"index_member_all 返回了无效 in_date：{invalid}")
        invalid_out = raw_out_dates.notna() & raw_out_dates.ne("") & out_dates.isna()
        if invalid_out.any():
            invalid = data.loc[invalid_out, "out_date"].head(10).tolist()
            raise ValueError(f"index_member_all 返回了无效 out_date：{invalid}")
        if (out_dates.notna() & out_dates.lt(in_dates)).any():
            raise ValueError("index_member_all 存在 out_date 早于 in_date 的记录")

        data["_in_date"] = in_dates
        data["_out_date"] = out_dates
        self._validate_intervals(data)
        data[INDUSTRY_FACTORS[0]] = data["l1_code"].map(
            SW_LEVEL1_TO_LEVEL0
        )
        if data[INDUSTRY_FACTORS[0]].isna().any():
            unknown = sorted(
                data.loc[
                    data[INDUSTRY_FACTORS[0]].isna(),
                    "l1_code",
                ].astype(str).unique()
            )
            raise ValueError(f"存在未映射的申万一级行业：{unknown}")
        for level, source, factor in (
            (1, "l1_code", INDUSTRY_FACTORS[1]),
            (2, "l2_code", INDUSTRY_FACTORS[2]),
            (3, "l3_code", INDUSTRY_FACTORS[3]),
        ):
            data[factor] = data[source].map(
                lambda value, current_level=level: industry_enum_value(
                    value,
                    current_level,
                )
            )

        relevant = data[
            data["_in_date"].le(self.end_date)
            & (
                data["_out_date"].isna()
                | data["_out_date"].ge(self.start_date)
            )
        ].copy()
        if relevant.empty:
            return self.EMPTY

        initial = pd.DataFrame({
            TIME_COLUMN: self.start_date,
            CODE_COLUMN: sorted(relevant["ts_code"].astype(str).unique()),
        })
        initial[TIME_COLUMN] = initial[TIME_COLUMN].astype("datetime64[ns]")
        for factor in self.factors:
            initial[factor] = float(IndustryLevel0.UNKNOWN)
        initial["_priority"] = 0

        starts = relevant.loc[
            :,
            ["ts_code", "_in_date", *self.factors],
        ].rename(
            columns={"ts_code": CODE_COLUMN, "_in_date": TIME_COLUMN}
        )
        starts[TIME_COLUMN] = starts[TIME_COLUMN].clip(
            lower=self.start_date,
        )
        starts["_priority"] = 2
        self._validate_start_events(starts)
        starts = starts.drop_duplicates(
            [TIME_COLUMN, CODE_COLUMN],
            keep="last",
        )

        resets = relevant.loc[
            relevant["_out_date"].notna(),
            ["ts_code", "_out_date"],
        ].rename(
            columns={"ts_code": CODE_COLUMN, "_out_date": TIME_COLUMN}
        )
        resets[TIME_COLUMN] = resets[TIME_COLUMN] + pd.offsets.Day(1)
        resets = resets[
            resets[TIME_COLUMN].between(self.start_date, self.end_date)
        ].copy()
        for factor in self.factors:
            resets[factor] = float(IndustryLevel0.UNKNOWN)
        resets["_priority"] = 1

        events = pd.concat(
            [initial, resets, starts],
            ignore_index=True,
        )
        events = events[events[TIME_COLUMN].le(self.end_date)]
        events = (
            events.sort_values(
                [TIME_COLUMN, CODE_COLUMN, "_priority"],
                kind="stable",
            )
            .drop_duplicates([TIME_COLUMN, CODE_COLUMN], keep="last")
        )
        events = events.melt(
            id_vars=[TIME_COLUMN, CODE_COLUMN],
            value_vars=list(self.factors),
            var_name=FACTOR_COLUMN,
            value_name=VALUE_COLUMN,
        )
        return self.normalize_result(events)

    def _validate_start_events(self, starts: pd.DataFrame) -> None:
        """拒绝同一股票同日出现互相冲突的行业归属。"""
        duplicates = starts.duplicated(
            [TIME_COLUMN, CODE_COLUMN],
            keep=False,
        )
        if not duplicates.any():
            return
        grouped = starts.loc[duplicates].groupby(
            [TIME_COLUMN, CODE_COLUMN],
            sort=False,
        )
        conflicts = grouped[list(self.factors)].nunique(dropna=False).gt(1).any(axis=1)
        if conflicts.any():
            samples = [
                f"{code}@{timestamp:%Y-%m-%d}"
                for timestamp, code in conflicts[conflicts].index[:10]
            ]
            raise ValueError(
                "同一股票同日存在冲突的申万行业归属：" + ", ".join(samples)
            )

    def _validate_intervals(self, data: pd.DataFrame) -> None:
        """拒绝同一股票重叠区间和多个最新行业归属。"""
        flags = data["is_new"].astype("string").str.strip().str.upper()
        if flags.isna().any() or flags.eq("").any():
            raise ValueError("index_member_all 返回了空 is_new")
        if invalid := sorted(set(flags.dropna()) - {"Y", "N"}):
            raise ValueError(f"index_member_all 返回了无效 is_new：{invalid}")
        current_counts = (
            data.loc[flags.eq("Y")]
            .groupby("ts_code", sort=False)
            .size()
        )
        if current_counts.gt(1).any():
            samples = current_counts[current_counts.gt(1)].index[:10].tolist()
            raise ValueError(f"股票存在多个最新申万行业归属：{samples}")

        ordered = data.sort_values(
            ["ts_code", "_in_date", "_out_date"],
            kind="stable",
        )
        grouped = ordered.groupby("ts_code", sort=False)
        has_previous = grouped.cumcount().gt(0)
        previous_out = grouped["_out_date"].shift()
        overlaps = has_previous & (
            previous_out.isna()
            | ordered["_in_date"].le(previous_out)
        )
        if overlaps.any():
            samples = ordered.loc[
                overlaps,
                ["ts_code", "_in_date", "_out_date"],
            ].head(10)
            formatted = [
                f"{code}@{in_date:%Y-%m-%d}"
                for code, in_date, _ in samples.itertuples(
                    index=False,
                    name=None,
                )
            ]
            raise ValueError(
                "同一股票存在重叠的申万行业有效区间："
                + ", ".join(formatted)
            )

    def fetch_all(self) -> Iterable[pd.DataFrame]:
        """从 coreData 水位重放最近事件并生成无状态增量结果。"""
        started = time.perf_counter()
        self.paginator.reset()
        last_date = None if self.overwrite else self.get_last_date()
        incremental_start = (
            self.start_date
            if last_date is None
            else max(self.start_date, last_date)
        )
        if incremental_start > self.end_date:
            logger.info(
                f"{self} 增量计划：无需更新，最近完整事件日="
                f"{last_date:%Y-%m-%d}，截止={self.end_date:%Y-%m-%d}"
            )
            return

        memberships = self.fetch_memberships()
        events = self.transform_memberships(memberships)
        result = events[
            events[TIME_COLUMN].between(incremental_start, self.end_date)
        ].reset_index(drop=True)
        elapsed = time.perf_counter() - started
        logger.info(
            f"{self} {'覆盖' if self.overwrite else '增量'}获取完成："
            f"成员区间={len(memberships):,}，事件行={len(result):,}，"
            f"实际起点={incremental_start:%Y-%m-%d}，"
            f"截止={self.end_date:%Y-%m-%d}"
            f"{self.paginator.summary()}，耗时={elapsed:.2f}秒"
        )
        yield result


__all__ = [
    "INDUSTRY_FACTORS",
    "INDUSTRY_LEVEL0_LABELS",
    "SW_LEVEL1_TO_LEVEL0",
    "IndustryLevel0",
    "IndustryWorker",
    "industry_enum_value",
]
