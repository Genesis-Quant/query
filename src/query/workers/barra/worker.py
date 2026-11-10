"""按自然年独立计算Barra；完整段校验上传后释放，不复用其它分段。"""

import json
import sys
from collections.abc import Iterator, Sequence
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd

from query.config import BarraConfig, DolphinSettings
from query.database.tables.barra import BarraTableWriter
from query.database.tables.core import core_table
from query.execute.api import execute_query
from query.utils import DateLike, get_codes, logger, normalize_date_range, normalize_str_list
from query.workers.core.industry import SW_LEVEL1_TO_LEVEL0, IndustryLevel0

from .industry import supplement_industry
from .merge import MERGE_SCRIPT
from .model import MODEL_SCRIPT
from .result import VARIABLES, BarraResult, release
from .source import DESCRIPTORS, dataset_query, industry_query


class BarraWorker:
    """借用调用方已显式initialize_query的会话，不更新CoreData或重算财报。"""

    def __init__(
        self, *, session: Any, start_date: DateLike = BarraConfig.start_date,
        end_date: DateLike | None = None, codes: Sequence[str] | None = None,
        settings: type[DolphinSettings] = DolphinSettings,
        config: type[BarraConfig] = BarraConfig, batch_size: int = 800_000,
    ) -> None:
        if session is None:
            raise TypeError("Barra需要已有的DolphinDB会话")
        if config.eigen_adjustment:
            raise ValueError("当前日频实现不启用教程的蒙特卡洛特征值调整")
        if config.industry_level not in (0, 1):
            raise ValueError("Barra行业层级只支持已有的0级或申万1级编码")
        for name in (
            "minimum_stocks", "covariance_window", "specific_window", "minimum_risk_observations",
            "min_specific_observations", "min_listing_days", "history_years", "report_years",
            "specific_peer_min_stocks", "specific_short_observations",
        ):
            value = getattr(config, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= np.iinfo(np.int32).max:
                raise ValueError(f"Barra {name}必须为INT范围内的正整数")
        if config.minimum_stocks < 2 or config.specific_short_observations < 2:
            raise ValueError("Barra截面和短历史风险至少需要两个有效观测")
        if not 0 < config.minimum_factor_coverage <= 1:
            raise ValueError("Barra描述子最低覆盖率必须位于(0,1]")
        if not 2 <= config.minimum_risk_observations <= config.covariance_window:
            raise ValueError("Barra因子风险最少观测数必须在[2,协方差窗口长度]内")
        if not 2 <= config.min_specific_observations <= config.specific_window:
            raise ValueError("Barra特异风险最少观测数必须在[2,特异风险窗口长度]内")
        if not isinstance(config.specific_peer_fallback, bool):
            raise TypeError("Barra specific_peer_fallback必须为bool")
        if isinstance(config.newey_west_lags, bool) or not isinstance(config.newey_west_lags, int) or not 0 <= config.newey_west_lags < min(config.covariance_window, config.specific_window):
            raise ValueError("Barra Newey-West阶数必须是小于窗口的非负整数")
        for name in ("covariance_half_life", "specific_half_life", "variance_floor", "exposure_limit"):
            value = getattr(config, name)
            if isinstance(value, bool) or not np.isfinite(value) or value <= 0:
                raise ValueError(f"Barra {name}必须是有限正数")
        if config.first_factors != BarraConfig.first_factors or config.second_factors != BarraConfig.second_factors:
            raise ValueError("当前DSL固定提供已有的36个描述子及其分层关系")
        if codes is not None and (isinstance(codes, (str, bytes)) or len(codes) == 0):
            raise ValueError("codes必须是非空证券序列；全市场请显式传None")
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
            raise ValueError("batch_size必须为正整数")
        self.session = session
        self.settings = settings
        self.config = config
        self.start_date, self.end_date = normalize_date_range(
            start_date, pd.Timestamp.today() if end_date is None else end_date,
        )
        self.codes = None if codes is None else normalize_str_list(list(codes), "codes", reject_duplicates=True)
        self.batch_size = batch_size
        self.partial_write_rows = 0
        self.active = False

    def __str__(self) -> str:
        return "<BarraWorker>"

    def segments(self) -> Iterator[tuple[pd.Timestamp, pd.Timestamp]]:
        """按自然年裁剪首尾日期，每一段都独立取数和计算。"""
        for year in range(self.start_date.year, self.end_date.year + 1):
            yield (
                max(self.start_date, pd.Timestamp(year=year, month=1, day=1)),
                min(self.end_date, pd.Timestamp(year=year, month=12, day=31)),
            )

    def get_calendar(self, start_date: DateLike, end_date: DateLike) -> pd.DatetimeIndex:
        """市场与基准互相核对；缺少已有交易日时不静默截断区间。"""
        start, end = normalize_date_range(start_date, end_date)
        dates = self.session.run(f"""
            (def(source,start,end,benchmark) {{
                market=select distinct timestamp(date(time)) as time from source
                    where factor=`close,time>=start,time<end,value>0,!isNanInf(value,true),
                        (endsWith(string(code),".SH") or endsWith(string(code),".SZ"))
                reference=select distinct timestamp(date(time)) as time from source
                    where code=symbol([benchmark])[0],factor=`pct_chg,time>=start,time<end,
                        isValid(value),!isNanInf(value,true)
                if (market.rows()==0 && reference.rows()==0) return array(TIMESTAMP,0)
                if (any(!(market.time in reference.time))) throw "Barra基准收益存在缺失交易日"
                if (any(!(reference.time in market.time))) throw "Barra市场行情存在整日缺失"
                return exec time from reference order by time
            }})({core_table(self.settings)},timestamp({start.value//1_000_000}l),
                timestamp({(end+pd.offsets.Day(1)).value//1_000_000}l),{json.dumps(self.config.benchmark)})
        """)
        return pd.DatetimeIndex(dates).as_unit("ms").normalize().drop_duplicates().sort_values()

    def _load_source(self, start: pd.Timestamp, end: pd.Timestamp, codes: list[str]) -> None:
        """一次取得整段日频描述子；财报直接使用现有窄表TTM，不调用财报接口。"""
        request = dataset_query(start.date(), end.date(), codes, config=self.config)
        columns = [
            "time", "code", "market_cap", "float_cap", "return_day", "benchmark_return",
            "return_valid", "eligible", "market_valid", "float_month_sum", "is_st", "history_observations",
            *DESCRIPTORS, "market_cap_proxy", "float_cap_proxy", "long_liability_proxy", "cost_proxy",
            "ebit_proxy", "dividend_proxy", "capital_disposal_proxy",
        ]
        phase = perf_counter()
        logger.info(
            f"[Barra DSL] 本段输入={start:%Y-%m-%d}至{end:%Y-%m-%d}，"
            f"原料及滚动计算={start-request.lookback:%Y-%m-%d}至{end:%Y-%m-%d}，"
            f"一次处理全部{len(codes):,}只证券，不复用其它分段数据"
        )
        with execute_query(request, session=self.session, settings=self.settings) as result:
            self.session.run(f"barraRaw=sql(sqlCol(symbol({json.dumps(columns)})),{result.data_ref}).eval();NULL")
        logger.info(f"[Barra DSL] 本段行情和36描述子完成，耗时={perf_counter()-phase:.2f}秒")
        phase = perf_counter()
        with execute_query(industry_query(start.date(), end.date(), codes, config=self.config),
                           session=self.session, settings=self.settings) as result:
            self.session.run(f"""
                barraIndustry=select time,string(code) as code,
                    industry_l{self.config.industry_level} as industry from {result.data_ref}
                NULL
            """)
        missing = self.session.run("""
            select time,string(code) as code from lj(barraRaw,barraIndustry,`time`code)
                where market_valid==true,(isNull(industry) || industry<=0)
        """)
        if not missing.empty:
            supplement = supplement_industry(missing, level=self.config.industry_level).dropna(subset=["industry"])
            if not supplement.empty:
                self.session.upload({"barraIndustrySupplement": supplement.rename(columns={"industry": "supplement"})})
                self.session.run("""
                    barraIndustry=select time,code,
                        iif(isValid(industry) && industry>0,industry,supplement) as industry
                        from lj(barraIndustry,barraIndustrySupplement,`time`code)
                    undef(`barraIndustrySupplement,VAR)
                    NULL
                """)
        logger.info(f"[Barra行业] 本段全部证券行业完成，耗时={perf_counter()-phase:.2f}秒")

    def _calculate_segment(self, start: pd.Timestamp, end: pd.Timestamp) -> BarraResult | None:
        """整段计算成功才交付结果；异常仅释放自己的会话对象。"""
        names = json.dumps(list(VARIABLES))
        self.session.run(f'if (any({names} in objs(true).name)) throw "当前会话已有未关闭的Barra结果";NULL')
        window = max(self.config.covariance_window, self.config.specific_window)
        calendar = self.get_calendar(start-pd.offsets.Day(window*2+30), end)
        output = calendar[(calendar >= start) & (calendar <= end)]
        if output.empty:
            logger.info(f"[Barra {start:%Y-%m-%d}至{end:%Y-%m-%d}] 没有已到齐的交易日，跳过本段")
            return None
        warmup = calendar[calendar < output[0]][-(window+1):]
        if len(warmup) < max(self.config.minimum_risk_observations, self.config.min_specific_observations):
            raise ValueError("Barra分段首个目标日风险预热不足")
        calendar = warmup.append(output)
        codes = list(get_codes()) if self.codes is None else list(self.codes)
        if not codes:
            raise ValueError("Barra证券域为空")
        config = self.config
        industries = (
            sorted(int(code.split(".")[0]) for code in SW_LEVEL1_TO_LEVEL0)
            if config.industry_level == 1
            else [int(value) for value in IndustryLevel0 if value != IndustryLevel0.UNKNOWN]
        )
        try:
            self.session.run(MERGE_SCRIPT)
            self.session.run(MODEL_SCRIPT)
            self.session.upload({
                "barraCalendar": calendar.to_numpy(dtype="datetime64[ms]"),
                "barraFirstFactors": {name: np.asarray(values, dtype=str) for name, values in config.first_factors.items()},
                "barraSecondFactors": {name: np.asarray(values, dtype=str) for name, values in config.second_factors.items()},
                "barraDescriptors": np.asarray(DESCRIPTORS, dtype=str),
                "barraStyleNames": np.asarray(config.styles, dtype=str),
                "barraRiskRequest": {
                    "start": np.datetime64(start, "ms"), "end": np.datetime64(end, "ms"),
                    "minimumStocks": np.int32(config.minimum_stocks),
                    "covarianceWindow": np.int32(config.covariance_window), "specificWindow": np.int32(config.specific_window),
                    "covarianceHalfLife": float(config.covariance_half_life), "specificHalfLife": float(config.specific_half_life),
                    "minimumObservations": np.int32(config.minimum_risk_observations),
                    "minimumSpecificObservations": np.int32(config.min_specific_observations),
                    "specificPeerFallback": config.specific_peer_fallback,
                    "specificPeerMinStocks": np.int32(config.specific_peer_min_stocks),
                    "specificShortObservations": np.int32(min(config.specific_short_observations, config.min_specific_observations)),
                    "lags": np.int32(config.newey_west_lags), "varianceFloor": float(config.variance_floor),
                    "shrink": config.specific_shrinkage, "industries": np.asarray(industries, dtype=np.int32),
                },
            })
            logger.info(
                f"[Barra {start:%Y-%m-%d}至{end:%Y-%m-%d}] 独立计算整段，"
                f"目标={len(output)}个交易日，本段风险预热={len(warmup)}个交易日"
            )
            self._load_source(calendar[0], output[-1], codes)
            self.session.run(f"""
                barraQuality=select count(*) as input_rows,sum(int(eligible)) as eligible_rows,
                    sum(int(market_valid)) as market_valid_rows,
                    sum(int(market_cap_proxy)) as market_cap_proxy_rows,
                    sum(int(float_cap_proxy)) as float_cap_proxy_rows,
                    sum(int(long_liability_proxy)) as long_liability_proxy_rows,
                    sum(int(cost_proxy)) as cost_proxy_rows,sum(int(ebit_proxy)) as ebit_proxy_rows,
                    sum(int(dividend_proxy)) as dividend_proxy_rows,
                    sum(int(capital_disposal_proxy)) as capital_disposal_proxy_rows from barraRaw group by time
                barraMerge=getRegTable(barraRaw,barraIndustry,barraDescriptors,
                    {config.minimum_factor_coverage},{config.minimum_stocks},true,{config.exposure_limit})
                barraStyles=getFSLevelFactor(barraMerge.data,barraFirstFactors,barraSecondFactors,{config.exposure_limit})
                NULL
            """)
            readiness = self.session.run("select * from barraMerge.readiness where time>=barraRiskRequest.start,time<=barraRiskRequest.end order by time")
            if not pd.DatetimeIndex(readiness["time"]).as_unit("ms").equals(output) or not readiness["ready"].all():
                raise ValueError("Barra整段描述子截面未齐，拒绝上传")
            self.session.run("barraResult=getRiskTables(barraStyles,barraRaw,barraCalendar,barraStyleNames,barraRiskRequest);NULL")
            coverage = self.session.run("select * from barraResult.risk_coverage order by time")
            if not pd.DatetimeIndex(coverage["time"]).as_unit("ms").equals(output):
                raise ValueError("Barra整段风险结果缺少目标交易日，拒绝上传")
            return BarraResult(session=self.session)
        except BaseException:
            try:
                release(self.session)
            except Exception as error:
                logger.warning(f"Barra分段失败后回收输入异常：{type(error).__name__}")
            raise

    def calculate(self, start_date: DateLike | None = None, end_date: DateLike | None = None) -> BarraResult:
        """只读计算单个自然年内的完整段；不创建或关闭调用方会话。"""
        start, end = normalize_date_range(
            self.start_date if start_date is None else start_date,
            self.end_date if end_date is None else end_date,
        )
        if not self.start_date <= start <= end <= self.end_date or start.year != end.year:
            raise ValueError("calculate区间必须位于Worker的start/end内且不跨年")
        if self.active:
            raise RuntimeError("当前Worker已有未结束的Barra计算")
        self.active = True
        try:
            result = self._calculate_segment(start, end)
            if result is None:
                raise ValueError("指定分段没有已到齐的交易日")
            return result
        finally:
            self.active = False

    def fetch_all(self) -> Iterator[dict[str, pd.DataFrame]]:
        """每段独立计算、校验并交付，当前结果释放后才进入下一年。"""
        if self.active:
            raise RuntimeError("当前Worker已有未结束的Barra计算")
        self.active = True
        try:
            for start, end in self.segments():
                result = self._calculate_segment(start, end)
                if result is None:
                    continue
                with result:
                    data = {name: getattr(result, name) for name in ("exposures", "covariance", "specific")}
                    self.check(data, config=self.config, calendar=pd.DatetimeIndex(result.calendar))
                    try:
                        yield data
                    finally:
                        del data
        finally:
            self.active = False

    @staticmethod
    def check(data: dict[str, pd.DataFrame], *, config: type[BarraConfig] = BarraConfig,
              calendar: pd.DatetimeIndex | None = None) -> dict[str, pd.DataFrame]:
        BarraTableWriter.check(data, config=config, calendar=calendar)
        return data

    def run(self) -> int:
        """只向Barra三表写入完整已校验段；不备份、不改上游、不复用旧结果。"""
        self.partial_write_rows = 0
        frames = self.fetch_all()
        try:
            for data in frames:
                writer = BarraTableWriter(self.session, settings=self.settings, config=self.config, batch_size=self.batch_size)
                try:
                    self.partial_write_rows += writer.write(data)
                except BaseException:
                    self.partial_write_rows += writer.partial_write_rows
                    raise
                logger.success(f"[Barra] 本段三表上传完成，累计={self.partial_write_rows:,}行")
                del data
        finally:
            failed = sys.exception() is not None
            try:
                frames.close()
            except Exception as error:
                if not failed:
                    raise
                logger.warning(f"Barra上传失败后回收分段异常：{type(error).__name__}")
        return self.partial_write_rows
