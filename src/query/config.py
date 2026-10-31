"""独立查询与数据更新配置；导入库时不读取 .env、不访问网络。"""

import os

from pydantic import SecretStr

from .settings import DolphinSettings

INDEX_CODES = tuple(filter(None, map(str.strip, os.getenv(
    "INDEX_CODES", "000016.SH,000300.SH,000905.SH,000852.SH"
).split(","))))
DATA_START_DATE = os.getenv("DATA_START_DATE", "2010-01-01")
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")


class WorkerSettings:
    """原 Worker 写入器配置，读写凭据严格分离。"""

    ENDPOINTS = DolphinSettings.environment_endpoints()
    HOST = ENDPOINTS[0].rsplit(":", 1)[0].strip("[]")
    PORT = int(ENDPOINTS[0].rsplit(":", 1)[1])
    DATABASE = os.getenv("DOLPHIN_CORE_DATABASE", "dfs://CoreData")
    TABLE = os.getenv("DOLPHIN_CORE_TABLE", "coreTable")
    RUNTIME_USERNAME = os.getenv("DOLPHINDB_USERNAME") or os.getenv("DOLPHIN_RUNTIME_USERNAME")
    RUNTIME_PASSWORD = os.getenv("DOLPHINDB_PASSWORD") or os.getenv("DOLPHIN_RUNTIME_PASSWORD")
    WORKER_USERNAME = os.getenv("DOLPHINDB_WORKER_USERNAME") or os.getenv("DOLPHIN_WORKER_USERNAME")
    WORKER_PASSWORD = os.getenv("DOLPHINDB_WORKER_PASSWORD") or os.getenv("DOLPHIN_WORKER_PASSWORD")
    HIGH_AVAILABILITY = False
    HIGH_AVAILABILITY_SITES = ENDPOINTS[1:]
    USE_PUBLIC_NAME = False

    @classmethod
    def credentials(cls, role: str) -> tuple[str, str]:
        if role == "runtime":
            username, password = cls.RUNTIME_USERNAME, cls.RUNTIME_PASSWORD
        elif role == "worker":
            username, password = cls.WORKER_USERNAME, cls.WORKER_PASSWORD
        else:
            raise ValueError(f"未知 DolphinDB 账号角色：{role}")
        if not username or not password:
            raise RuntimeError(f"缺少 DolphinDB {role} 专用账号配置")
        return username, password

    @classmethod
    def session_settings(cls, role: str) -> DolphinSettings:
        username, password = cls.credentials(role)
        return DolphinSettings(endpoints=cls.ENDPOINTS, username=username,
                              password=SecretStr(password), database=cls.DATABASE, table=cls.TABLE)
