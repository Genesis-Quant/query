"""独立Barra库的三张长表；完整年段校验后替换并上传。"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from query.config import BarraConfig, DolphinSettings

from .core import grant_runtime_table_read

COLUMNS = {
    "exposures": ("time", "code", "factor", "value"),
    "covariance": ("time", "factor1", "factor2", "value"),
    "specific": ("time", "code", "value"),
}


class BarraTableWriter:
    """一次接收已算完的年段三表；不读取旧结果作为计算输入。"""

    def __init__(self, session: Any, *, settings: type[DolphinSettings] = DolphinSettings,
                 config: type[BarraConfig] = BarraConfig, batch_size: int = 800_000) -> None:
        self.session, self.settings, self.batch_size = session, settings, batch_size
        self.config = config
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
            if getattr(settings, "username", None):
                grant_runtime_table_read(self.session, settings.barra_database, table, settings)
        self.prepared = True

    @staticmethod
    def check(data: dict[str, pd.DataFrame], *, config: type[BarraConfig] = BarraConfig,
              calendar: pd.DatetimeIndex | None = None) -> None:
        """整段上传前逐日核对真实模型轴、三表日期和半正定协方差。"""
        from query.workers.core.industry import SW_LEVEL1_TO_LEVEL0, IndustryLevel0

        if config.industry_level == 1:
            industries = {int(code.split('.')[0]) for code in SW_LEVEL1_TO_LEVEL0}
        elif config.industry_level == 0:
            industries = {int(value) for value in IndustryLevel0 if value != IndustryLevel0.UNKNOWN}
        else:
            raise ValueError("Barra行业层级只支持已有的0级或申万1级编码")
        expected = {"country", *config.styles, *(f"industry_{value}" for value in industries)}
        dates = None
        grouped = {}
        for name, columns in COLUMNS.items():
            frame = data[name]
            if tuple(frame.columns) != columns or frame.empty:
                raise ValueError(f"{name}为空或字段不符")
            if frame.iloc[:, :-1].isna().any().any() or frame.duplicated(list(columns[:-1])).any():
                raise ValueError(f"{name}存在空键或重复键")
            if not np.isfinite(frame["value"].to_numpy(dtype=float)).all():
                raise ValueError(f"{name}有非有限值")
            clock = pd.DatetimeIndex(frame["time"])
            if clock.tz is not None or not clock.equals(clock.normalize()):
                raise ValueError(f"{name}日期必须是无时区交易日零点")
            current = clock.as_unit("ms").unique().sort_values()
            if current[0].year != current[-1].year:
                raise ValueError("Barra单次上传必须位于同一个自然年内")
            if dates is not None and not current.equals(dates):
                raise ValueError("Barra三表的交易日集合不一致")
            dates = current
            grouped[name] = frame.groupby("time", sort=True)
        if calendar is not None and not dates.equals(pd.DatetimeIndex(calendar).as_unit("ms")):
            raise ValueError("Barra结果交易日与本段目标日历不一致")
        factors = set(data["exposures"]["factor"])
        if factors != expected:
            raise ValueError(f"Barra模型因子轴不符：缺失={sorted(expected-factors)}，多余={sorted(factors-expected)}")
        for current, x in grouped["exposures"]:
            f = grouped["covariance"].get_group(current)
            d = grouped["specific"].get_group(current)
            codes = set(x["code"])
            style = x.loc[x["factor"].isin(config.styles), "value"]
            if style.abs().gt(config.exposure_limit + 1e-12).any():
                raise ValueError(f"Barra {current}风格暴露超过质量上限")
            country = x.loc[x["factor"].eq("country"), "value"]
            if not country.eq(1.0).all():
                raise ValueError(f"Barra {current}国家因子必须为1")
            industry = x.loc[x["factor"].str.startswith("industry_")]
            if not industry.empty and (
                not industry["value"].isin([0.0, 1.0]).all()
                or not industry.groupby("code")["value"].sum().eq(1.0).all()
            ):
                raise ValueError(f"Barra {current}行业暴露必须为唯一独热编码")
            if set(x["factor"]) != factors or len(x) != len(codes)*len(factors) or codes != set(d["code"]):
                raise ValueError(f"Barra {current}股票暴露与特异风险覆盖不一致")
            if not d["value"].gt(0).all() or len(f) != len(factors)**2:
                raise ValueError(f"Barra {current}特异方差不为正或因子协方差不完整")
            if set(f["factor1"]) != factors or set(f["factor2"]) != factors:
                raise ValueError(f"Barra {current}协方差与暴露的因子轴不一致")
            axis = sorted(factors)
            matrix = f.pivot(index="factor1", columns="factor2", values="value").reindex(index=axis, columns=axis).to_numpy()
            if not np.isfinite(matrix).all() or not np.allclose(matrix, matrix.T, atol=1e-12):
                raise ValueError(f"Barra {current}因子协方差缺值或不对称")
            if np.linalg.eigvalsh(matrix).min() < -1e-10:
                raise ValueError(f"Barra {current}因子协方差不是半正定矩阵")

    def write(self, data: dict[str, pd.DataFrame]) -> int:
        """先校验完整分段，再替换该段三表；不宣称跨表原子事务。"""
        self.partial_write_rows = 0
        self.check(data, config=self.config)
        self.prepare()
        dates = pd.DatetimeIndex(data["exposures"]["time"]).as_unit("ms").unique().sort_values()
        self.session.upload({"barraWriteDates": dates.to_numpy(dtype="datetime64[ms]")})
        targets = {
            name: f"loadTable({json.dumps(self.settings.barra_database)},{json.dumps(table)})"
            for name, table in self.tables.items()
        }
        for target in targets.values():
            self.session.run(f"select count(*) as rows,min(time) as first_date,max(time) as last_date from {target} where time in barraWriteDates")
        for name, target in targets.items():
            self.session.run(f"delete from {target} where time in barraWriteDates")
            frame = data[name]
            for offset in range(0, len(frame), self.batch_size):
                batch = frame.iloc[offset:offset+self.batch_size].copy()
                batch["time"] = pd.to_datetime(batch["time"]).astype("datetime64[ms]")
                self.session.upload({"barraBatch": batch})
                written = int(self.session.run(f"tableInsert({target},barraBatch)"))
                self.partial_write_rows += written
                if written != len(batch):
                    raise RuntimeError(f"{self.tables[name]}批次写入数量不符")
            actual = self.session.run(f"""
                select count(*) as rows from {target}
                where time in barraWriteDates group by time order by time
            """)
            expected = frame.groupby("time", sort=True).size()
            if not pd.DatetimeIndex(actual["time"]).as_unit("ms").equals(pd.DatetimeIndex(expected.index).as_unit("ms")) or not np.array_equal(actual["rows"].to_numpy(), expected.to_numpy()):
                raise RuntimeError(f"{self.tables[name]}整段逐日写入数量校验失败")
        return self.partial_write_rows
