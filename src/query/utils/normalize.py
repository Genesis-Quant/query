"""提供数据更新和查询共用的日期标准化。"""

from datetime import date, datetime
from typing import Any

import pandas as pd

DateLike = date | datetime | pd.Timestamp | str


def normalize_date(value: DateLike, name: str = "date") -> pd.Timestamp:
    """把日期输入规范为无时区的零点 Timestamp。"""
    try:
        result = pd.Timestamp(value)
    except Exception as error:
        raise ValueError(f"{name} 不是有效日期：{value!r}") from error
    if not isinstance(result, pd.Timestamp):
        raise ValueError(f"{name} 不是有效日期：{value!r}")
    if result.tzinfo is not None:
        result = result.tz_localize(None)
    return result.normalize()


def normalize_date_range(
        start_date: DateLike,
        end_date: DateLike,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """规范闭区间日期并拒绝倒置区间。"""
    start = normalize_date(start_date, "start_date")
    end = normalize_date(end_date, "end_date")
    if start > end:
        raise ValueError("start_date 不能晚于 end_date")
    return start, end


def normalize_str(value: Any, location: str) -> str:
    """清理单个字符串并拒绝空值。"""
    if not isinstance(value, str):
        raise ValueError(f"{location} 必须是字符串")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{location} 不能为空")
    return normalized


def normalize_str_list(
        values: Any,
        location: str,
        *,
        reject_duplicates: bool = False,
) -> list[str]:
    """清理字符串列表，在保持顺序的同时处理重复项并拒绝空值。"""
    if not isinstance(values, list):
        raise ValueError(f"{location} 必须是 list[str]")
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_str(value, location)
        if normalized in seen:
            if reject_duplicates:
                raise ValueError(f"{location} 不能包含重复值：{normalized!r}")
            continue
        result.append(normalized)
        seen.add(normalized)
    return result
