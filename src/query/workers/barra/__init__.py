"""Barra DSL取数和DOS计算入口；会话由调用方显式初始化并管理。"""

from .result import BarraResult
from .source import DESCRIPTORS, dataset_query, industry_query
from .worker import BarraWorker

__all__ = ["DESCRIPTORS", "BarraResult", "BarraWorker", "dataset_query", "industry_query"]
