"""只在本次Barra计算内补充缺失行业，不修改CoreData或通用行业Worker。"""

import numpy as np
import pandas as pd

from query.utils import RateLimiter, Retry, logger
from query.utils.ts_api import get_pro
from query.workers.core.base.worker import Paginator
from query.workers.core.industry import SW_LEVEL1_TO_LEVEL0


def supplement_industry(missing: pd.DataFrame, *, level: int) -> pd.DataFrame:
    """仅接受另一成员接口的唯一直接一级归属，冲突和无证据仍保留缺失。"""
    result = missing.loc[:, ["time", "code"]].drop_duplicates().copy()
    result["time"] = pd.to_datetime(result["time"]).astype("datetime64[ms]")
    result["industry"] = np.nan
    if result.empty:
        return result
    if level not in (0, 1):
        raise ValueError("Barra行业层级只支持0或1")

    pager = Paginator(Retry(max_retries=3, retry_interval=1.0, limiter=RateLimiter(4)))
    conflicts = 0
    for code, targets in result.groupby("code", sort=False):
        history = pager.fetch(
            get_pro().index_member,
            params={"ts_code": str(code), "fields": "index_code,con_code,in_date,out_date"},
            page_size=2_000,
            context=f"[Barra行业补充 {code}]",
            stop_on_short=False,
        )
        if history.empty:
            continue
        required = {"index_code", "con_code", "in_date", "out_date"}
        if not required.issubset(history.columns):
            raise ValueError(f"Barra行业来源缺少字段：{sorted(required-set(history.columns))}")
        if not history["con_code"].astype(str).eq(str(code)).all():
            raise ValueError(f"Barra行业来源返回其它证券：{code}")
        history = history.loc[history["index_code"].isin(SW_LEVEL1_TO_LEVEL0)].copy()
        if history.empty:
            continue
        starts = pd.to_datetime(history["in_date"], format="%Y%m%d", errors="coerce")
        raw_ends = history["out_date"].astype("string").str.strip()
        ends = pd.to_datetime(raw_ends.where(raw_ends.ne("")), format="%Y%m%d", errors="coerce")
        invalid_end = raw_ends.notna() & raw_ends.ne("") & ends.isna()
        if starts.isna().any() or invalid_end.any() or (ends.notna() & ends.lt(starts)).any():
            raise ValueError(f"Barra行业来源存在无效区间：{code}")

        days = pd.DatetimeIndex(targets["time"])
        counts = np.zeros(len(days), dtype=int)
        values = np.full(len(days), np.nan)
        for industry in history["index_code"].unique():
            active = np.zeros(len(days), dtype=bool)
            for position in np.flatnonzero(history["index_code"].eq(industry).to_numpy()):
                start, end = starts.iloc[position], ends.iloc[position]
                active |= (days >= start) & (True if pd.isna(end) else days <= end)
            counts += active
            value = int(str(industry).split(".")[0]) if level == 1 else int(SW_LEVEL1_TO_LEVEL0[industry])
            values[active] = float(value)
        values[counts != 1] = np.nan
        result.loc[targets.index, "industry"] = values
        conflicts += int((counts > 1).sum())
    logger.info(
        f"[Barra行业补充] 缺口={len(result):,}证券日，"
        f"直接历史归属={int(result['industry'].notna().sum()):,}，冲突={conflicts:,}，仅用于本段计算"
    )
    return result
