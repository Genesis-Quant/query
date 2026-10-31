"""提供通用文件写入能力。"""

import os
from pathlib import Path
from uuid import uuid4


def atomic_write_text(path: Path | str, content: str) -> Path:
    """使用同目录临时文件原子替换目标文本文件。"""
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
