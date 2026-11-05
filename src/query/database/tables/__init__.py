"""CoreData因子窄表和独立Barra风险结果表。"""

from .barra import BarraTableWriter
from .core import CORE_TABLE, CoreTableWriter

__all__ = ["CORE_TABLE", "CoreTableWriter", "BarraTableWriter"]
