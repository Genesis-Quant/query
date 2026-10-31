"""查询会话连接与数据表配置。"""

import os
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator


class DolphinSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    endpoints: tuple[str, ...] = ("dolphindb:8848",)
    username: str
    password: SecretStr
    database: str = "dfs://CoreData"
    table: str = "coreTable"

    @field_validator("endpoints", mode="before")
    @classmethod
    def validate_endpoints(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            value = value.split(",")
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError("DolphinDB 至少需要一个端点")
        endpoints = []
        for endpoint in value:
            if not isinstance(endpoint, str):
                raise ValueError("DolphinDB 端点必须是 host:port 字符串")
            endpoint = endpoint.strip()
            if not endpoint or any(char.isspace() or char in "/?#@\\" for char in endpoint):
                raise ValueError("DolphinDB 端点只接受 host:port，IPv6 使用 [host]:port")
            try:
                address = urlsplit(f"//{endpoint}")
                host, port = address.hostname, address.port
            except ValueError:
                raise ValueError("DolphinDB 端点格式无效，IPv6 使用 [host]:port") from None
            if not host or port is None or not 1 <= port <= 65535:
                raise ValueError("DolphinDB 端点必须包含主机和 1 至 65535 的端口")
            if endpoint.rsplit(":", 1)[0].lower() != (f"[{host}]" if ":" in host else host):
                raise ValueError("DolphinDB 端点格式无效，IPv6 使用 [host]:port")
            endpoints.append(f"[{host}]:{port}" if ":" in host else f"{host}:{port}")
        return tuple(dict.fromkeys(endpoints))

    @classmethod
    def environment_endpoints(cls) -> tuple[str, ...]:
        configured = os.getenv("DOLPHINDB_ENDPOINTS")
        if configured is None:
            first = f"{os.getenv('DOLPHIN_HOST', 'dolphindb')}:{os.getenv('DOLPHIN_PORT', '8848')}"
            configured = first + "," + os.getenv("DOLPHIN_HIGH_AVAILABILITY_SITES", "")
        values = tuple(value.strip() for value in configured.split(",") if value.strip())
        return cls.validate_endpoints(values)

    @classmethod
    def from_env(cls, *, role: str = "runtime") -> "DolphinSettings":
        if role == "runtime":
            username = os.getenv("DOLPHINDB_USERNAME") or os.getenv("DOLPHIN_RUNTIME_USERNAME")
            password = os.getenv("DOLPHINDB_PASSWORD") or os.getenv("DOLPHIN_RUNTIME_PASSWORD")
        elif role == "worker":
            username = os.getenv("DOLPHINDB_WORKER_USERNAME") or os.getenv("DOLPHIN_WORKER_USERNAME")
            password = os.getenv("DOLPHINDB_WORKER_PASSWORD") or os.getenv("DOLPHIN_WORKER_PASSWORD")
        else:
            raise ValueError(f"未知 DolphinDB 账号角色：{role}")
        if not username or not password:
            raise RuntimeError(f"缺少 DolphinDB {role} 专用账号配置")
        return cls(endpoints=cls.environment_endpoints(), username=username,
                   password=SecretStr(password),
                   database=os.getenv("DOLPHIN_CORE_DATABASE", "dfs://CoreData"),
                   table=os.getenv("DOLPHIN_CORE_TABLE", "coreTable"))
