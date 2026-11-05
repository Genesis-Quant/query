"""独立 Barra 库的三张长表、权限、完整日写入与增量读取。"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from query.config import DolphinSettings

from .core import grant_runtime_table_read

COLUMNS = {
    "exposures": ("time", "code", "factor", "value"),
    "covariance": ("time", "factor1", "factor2", "value"),
    "specific": ("time", "code", "value"),
}


class BarraTableWriter:
    """按交易日完整替换三表；不把单表最大日期当作完整进度。"""

    def __init__(self, session: Any, *, settings: type[DolphinSettings] = DolphinSettings,
                 batch_size: int = 800_000) -> None:
        self.session, self.settings, self.batch_size = session, settings, batch_size
        self.tables = {
            "exposures": settings.barra_table,
            "covariance": settings.barra_cov_table,
            "specific": settings.barra_sp_table,
        }
        if batch_size <= 0 or len(set(self.tables.values())) != 3:
            raise ValueError("batch_size必须为正，Barra三张表名必须不同")
        self.prepared = False
        self.partial_write_rows = 0

    def exists(self, name: str) -> bool:
        return bool(self.session.run(
            f"existsTable({json.dumps(self.settings.barra_database)},{json.dumps(self.tables[name])})"
        ))

    def prepare(self) -> None:
        """新库按月RANGE分区；已有库表结构不符则报错，不自动迁移。"""
        if self.prepared:
            return
        settings = self.settings
        self.session.upload({"barraDatabase": settings.barra_database,
                             "barraTables": np.asarray(list(self.tables.values()), dtype=str)})
        self.session.run(r"""
            def initializeBarraDatabase(dbName,names) {
                if (!existsDatabase(dbName))
                    database(dbName,RANGE,date(datetimeAdd(1990.01M,0..1332,"M")),engine="TSDB")
                db=database(dbName)
                info=schema(db)
                if (info.engineType!="TSDB" || info.partitionType!=RANGE)
                    throw "Barra数据库必须采用TSDB和时间RANGE分区"
                if (!existsTable(dbName,names[0]))
                    db.createPartitionedTable(
                        table(1:0,`time`code`factor`value,[TIMESTAMP,SYMBOL,SYMBOL,DOUBLE]),
                        names[0],`time,sortColumns=`code`factor`time,keepDuplicates=LAST,
                        sortKeyMappingFunction=[hashBucket{,40},hashBucket{,40}])
                if (!existsTable(dbName,names[1]))
                    db.createPartitionedTable(
                        table(1:0,`time`factor1`factor2`value,[TIMESTAMP,SYMBOL,SYMBOL,DOUBLE]),
                        names[1],`time,sortColumns=`factor1`factor2`time,keepDuplicates=LAST)
                if (!existsTable(dbName,names[2]))
                    db.createPartitionedTable(
                        table(1:0,`time`code`value,[TIMESTAMP,SYMBOL,DOUBLE]),
                        names[2],`time,sortColumns=`code`time,keepDuplicates=LAST,
                        sortKeyMappingFunction=[hashBucket{,500}])
            }
            initializeBarraDatabase(barraDatabase,barraTables)
        """)
        for name, table in self.tables.items():
            definitions = self.session.run(
                f"schema(loadTable({json.dumps(settings.barra_database)},{json.dumps(table)})).colDefs"
            )
            columns = COLUMNS[name]
            types = ("TIMESTAMP", *("SYMBOL" for _ in columns[1:-1]), "DOUBLE")
            if tuple(definitions["name"]) != columns or tuple(definitions["typeString"]) != types:
                raise ValueError(f"已有{table}结构不符，不会覆盖")
            grant_runtime_table_read(self.session, settings.barra_database, table, settings)
        self.prepared = True

    def summaries(self, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, pd.DataFrame]:
        """只读检查区间中的缺日与三表覆盖，不建库、不写入。"""
        self.session.upload({"barraStart": np.datetime64(start, "ms"),
                             "barraEnd": np.datetime64(end, "ms")})
        dimensions = {
            "exposures": "count(*) as rows,nunique(code) as codes,nunique(factor) as factors",
            "covariance": "count(*) as rows,nunique(factor1) as factors,nunique(factor2) as factors2",
            "specific": "count(*) as rows,nunique(code) as codes",
        }
        results = {}
        for name, table in self.tables.items():
            results[name] = self.session.run(f"""
                select {dimensions[name]} from loadTable(
                    {json.dumps(self.settings.barra_database)},{json.dumps(table)})
                where time>=barraStart,time<=barraEnd group by time order by time
            """) if self.exists(name) else pd.DataFrame()
        return results

    def read_exposures(self, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        if not self.exists("exposures"):
            return pd.DataFrame(columns=COLUMNS["exposures"])
        self.session.upload({"barraStart": np.datetime64(start, "ms"),
                             "barraEnd": np.datetime64(end, "ms")})
        return self.session.run(f"""
            select time,code,factor,value from loadTable(
                {json.dumps(self.settings.barra_database)},{json.dumps(self.tables['exposures'])})
            where time>=barraStart,time<=barraEnd order by time,code,factor
        """)

    def check(self, data: dict[str, pd.DataFrame]) -> None:
        """写入前验证唯一键、同日覆盖、有限值及完整半正定协方差。"""
        dates = set()
        for name, columns in COLUMNS.items():
            frame = data[name]
            if tuple(frame.columns) != columns or frame.empty:
                raise ValueError(f"{name}为空或字段不符")
            if frame.iloc[:, :-1].isna().any().any() or frame.duplicated(list(columns[:-1])).any():
                raise ValueError(f"{name}存在空键或重复键")
            if not np.isfinite(frame["value"].to_numpy(dtype=float)).all():
                raise ValueError(f"{name}有非有限值")
            dates.update(pd.Timestamp(date) for date in frame["time"].unique())
        if len(dates) != 1:
            raise ValueError("三表必须是同一个交易日")
        x, f, d = data["exposures"], data["covariance"], data["specific"]
        codes, factors = set(x["code"]), sorted(set(x["factor"]))
        if len(x) != len(codes)*len(factors) or codes != set(d["code"]):
            raise ValueError("股票暴露与特异风险覆盖不一致")
        if not d["value"].gt(0).all() or len(f) != len(factors)**2:
            raise ValueError("特异方差不为正或因子协方差不完整")
        matrix = f.pivot(index="factor1", columns="factor2", values="value").reindex(index=factors, columns=factors).to_numpy()
        if not np.isfinite(matrix).all() or not np.allclose(matrix, matrix.T, atol=1e-12):
            raise ValueError("因子协方差缺值或不对称")
        if np.linalg.eigvalsh(matrix).min() < -1e-10:
            raise ValueError("因子协方差不是半正定矩阵")

    def write(self, data: dict[str, pd.DataFrame]) -> int:
        """完整替换一天；失败立即停止，下一次从最早异常或尾日重放。"""
        self.partial_write_rows = 0
        self.check(data)
        self.prepare()
        date = pd.Timestamp(data["exposures"]["time"].iloc[0])
        self.session.upload({"barraDate": np.datetime64(date, "ms")})
        # 不宣称跨三表原子事务；数据消费者在更新任务成功后读取。
        for name, table in self.tables.items():
            target = f"loadTable({json.dumps(self.settings.barra_database)},{json.dumps(table)})"
            self.session.run(f"delete from {target} where time=barraDate")
            frame = data[name]
            for offset in range(0, len(frame), self.batch_size):
                batch = frame.iloc[offset:offset+self.batch_size].copy()
                batch["time"] = pd.to_datetime(batch["time"]).astype("datetime64[ms]")
                self.session.upload({"barraBatch": batch})
                written = int(self.session.run(f"tableInsert({target},barraBatch)"))
                if written != len(batch):
                    raise RuntimeError(f"{table}批次写入数量不符")
                self.partial_write_rows += written
            count = int(self.session.run(f"exec count(*) from {target} where time=barraDate"))
            if count != len(frame):
                raise RuntimeError(f"{table}当日写入校验失败")
        return self.partial_write_rows
