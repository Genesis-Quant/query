"""Barra会话结果：按需下载，不持有或关闭调用方连接。"""

from collections.abc import Sequence
from typing import Any

from query.utils import SessionResult, logger

VARIABLES = (
    "barraRaw", "barraIndustry", "barraCalendar", "barraMerge", "barraStyles", "barraResult",
    "barraFirstFactors", "barraSecondFactors", "barraDescriptors", "barraStyleNames",
    "barraRiskRequest", "barraQuality", "barraDatabase", "barraTables", "barraStart", "barraEnd",
    "barraBatch", "barraWriteDates", "barraIndustrySupplement",
)


def release(session: Any, variables: Sequence[str] = VARIABLES) -> None:
    session.run("\n".join(
        f'if ("{name}" in objs(true).name) undef("{name}", VAR)' for name in variables
    ) + "\nNULL")


class BarraResult(SessionResult):
    """原始36因子、合成因子、三张结果和质量统计均保留在本次会话内。"""

    data_ref = "barraResult"

    @property
    def calendar(self):
        return self.download("barraCalendar[barraCalendar >= barraRiskRequest.start && barraCalendar <= barraRiskRequest.end]")

    @property
    def raw_data(self):
        return self.download("barraRaw")

    @property
    def descriptors(self):
        return self.download("barraMerge.data")

    @property
    def styles(self):
        return self.download("barraStyles")

    @property
    def quality(self):
        return self.download("barraQuality")

    @property
    def coverage(self):
        return self.download("barraMerge.coverage")

    @property
    def readiness(self):
        return self.download("barraMerge.readiness")

    @property
    def stock_coverage(self):
        return self.download("barraMerge.stock_coverage")

    @property
    def exposures(self):
        return self.download("barraResult.exposures")

    @property
    def covariance(self):
        return self.download("barraResult.covariance")

    @property
    def specific(self):
        return self.download("barraResult.specific")

    @property
    def factor_returns(self):
        return self.download("barraResult.factor_returns")

    @property
    def specific_returns(self):
        return self.download("barraResult.specific_returns")

    @property
    def regression(self):
        return self.download("barraResult.regression")

    @property
    def risk_coverage(self):
        return self.download("barraResult.risk_coverage")

    @property
    def specific_audit(self):
        return self.download("barraResult.specific_audit")

    def close(self) -> None:
        if self.closed:
            return
        try:
            release(self.session)
        finally:
            super().close()

    def __exit__(self, exception_type, exception, traceback) -> bool:
        try:
            self.close()
        except Exception as error:
            if exception_type is None:
                raise
            logger.warning(f"Barra异常退出时回收结果失败：{type(error).__name__}")
        return False
