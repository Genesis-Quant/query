"""使用调用方已有会话管理CoreData分区并写入因子长表。"""

import json
from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from query.config import DolphinSettings
from query.utils import CODE_COLUMN, CORE_COLUMNS, FACTOR_COLUMN, TIME_COLUMN, VALUE_COLUMN, logger


def ddb_string(value: str) -> str:
    """生成安全的 DolphinDB 字符串字面量。"""
    return json.dumps(value, ensure_ascii=False)


def normalize_factors(values: Iterable[str]) -> list[str]:
    """清理、去重并校验统一长表的 factor 列表。"""
    factors: list[str] = []
    for value in values:
        if value is None:
            continue
        factor = str(value).strip()
        if factor and factor not in factors:
            factors.append(factor)
    if not factors:
        raise ValueError("factor 至少包含一个非空值")
    return factors


def core_table(settings: type[DolphinSettings] = DolphinSettings) -> str:
    """按本次读写配置生成同一因子表引用。"""
    return (
        f"loadTable({ddb_string(settings.core_database)}, "
        f"{ddb_string(settings.core_table)})"
    )


CORE_TABLE = core_table()


def grant_runtime_table_read(
    session: Any, database: str, table: str,
    settings: type[DolphinSettings] = DolphinSettings,
) -> None:
    """由表所有者授予业务运行账号指定表的只读权限。"""
    username = getattr(settings, "username", None)
    if not username:
        raise RuntimeError("授予runtime读权限需要显式提供settings.username")
    session.run(f"grant({ddb_string(username)}, TABLE_READ, {ddb_string(database+'/'+table)})")


def ensure_core_table(
    session: Any, factors: list[str], settings: type[DolphinSettings] = DolphinSettings,
) -> None:
    """确保统一因子表存在，不改变已有表结构。"""
    session.upload({
        "coreDatabaseName": settings.core_database,
        "coreTableName": settings.core_table,
        "coreInitialFactors": np.asarray(factors, dtype=str),
    })
    session.run(f"""
        def initializeCoreDatabase(dbName, tableName, initialFactors) {{
            // 创建按月和 factor 组合分区的统一 TSDB 长表。
            if (size(initialFactors) == 0) throw "initialFactors 不能为空"
            if (!existsDatabase(dbName)) {{
                database(
                    directory=dbName, partitionType=COMPO,
                    partitionScheme=[
                        database(, RANGE, date(datetimeAdd(1990.01M, 0..61*12, "M"))),
                        database(, VALUE, symbol(initialFactors))
                    ], engine="TSDB"
                )
            }}
            db = database(dbName)
            if (!existsTable(dbName, tableName)) {{
                db.createPartitionedTable(
                    table=table(1:0,
                        ["{TIME_COLUMN}", "{CODE_COLUMN}", "{FACTOR_COLUMN}", "{VALUE_COLUMN}"],
                        [TIMESTAMP, SYMBOL, SYMBOL, DOUBLE]),
                    tableName=tableName,
                    partitionColumns=["{TIME_COLUMN}", "{FACTOR_COLUMN}"],
                    sortColumns=[`{CODE_COLUMN}, `{TIME_COLUMN}],
                    keepDuplicates=LAST, sortKeyMappingFunction=[hashBucket{{,500}}]
                )
            }}
        }}
        initializeCoreDatabase(coreDatabaseName, coreTableName, coreInitialFactors)
    """)
    grant_runtime_table_read(session, settings.core_database, settings.core_table, settings)


def ensure_factor_partitions(
    values: Iterable[str], *, session: Any,
    settings: type[DolphinSettings] = DolphinSettings,
) -> list[str]:
    """在已有会话内补建缺失的factor分区，不创建或关闭连接。"""
    if session is None:
        raise TypeError("session 必须是已有的 DolphinDB 会话")
    factors = normalize_factors(values)
    ensure_core_table(session, factors, settings)
    schema = session.run(f"schema(database({ddb_string(settings.core_database)}))")
    existing = {str(value) for value in schema["partitionSchema"][1]}
    missing = [factor for factor in factors if factor not in existing]
    if missing:
        logger.info(f"DolphinDB 新增 {len(missing):,} 个 factor 分区：{missing[:10]}")
        session.upload({"coreNewFactorPartitions": np.asarray(missing, dtype=str)})
        session.run(
            f"addValuePartitions(database({ddb_string(settings.core_database)}), "
            "symbol(coreNewFactorPartitions), 1)"
        )
    return missing


class CoreTableWriter:
    """在调用方已有会话内追加规范的四列成品，不隐式创建连接池。"""

    def __init__(
        self, factors: Iterable[str], *, session: Any,
        settings: type[DolphinSettings] = DolphinSettings,
    ) -> None:
        if session is None:
            raise TypeError("session 必须是已有的 DolphinDB 会话")
        self.session = session
        self.settings = settings
        self.factors = tuple(normalize_factors(factors))
        self.factor_set = set(self.factors)
        self.prepared = False
        self.closed = False

    def prepare(self) -> None:
        """确保库表和分区存在，不创建连接。"""
        if self.closed:
            raise RuntimeError("CoreTableWriter 已关闭")
        if not self.prepared:
            ensure_factor_partitions(self.factors, session=self.session, settings=self.settings)
            self.prepared = True

    def append(self, data: pd.DataFrame) -> int:
        """原样追加四列成品并核对写入行数，不再次清洗数据。"""
        if self.closed:
            raise RuntimeError("CoreTableWriter 已关闭")
        if not isinstance(data, pd.DataFrame):
            raise TypeError("待写入数据必须是 pandas.DataFrame")
        if tuple(data.columns) != CORE_COLUMNS:
            raise ValueError(f"待写入数据列必须严格为 {list(CORE_COLUMNS)}")
        if data.empty:
            return 0
        if unknown := set(data[FACTOR_COLUMN].unique()) - self.factor_set:
            raise ValueError(f"待写入数据包含未声明 factor：{sorted(unknown)}")
        self.prepare()
        self.session.upload({"coreWriteBatch": data})
        target = core_table(self.settings)
        try:
            rows = int(self.session.run(f"tableInsert({target}, coreWriteBatch)"))
        finally:
            try:
                self.session.run('if ("coreWriteBatch" in objs(true).name) undef("coreWriteBatch", VAR); NULL')
            except Exception as error:
                logger.warning(f"清理写入临时表失败：{type(error).__name__}")
        if rows != len(data):
            raise RuntimeError(f"DolphinDB 写入行数不一致：预期 {len(data):,}，实际 {rows:,}")
        return rows

    def close(self) -> None:
        """关闭写入器，不关闭调用方会话。"""
        self.closed = True

    def __enter__(self) -> "CoreTableWriter":
        self.prepare()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()
