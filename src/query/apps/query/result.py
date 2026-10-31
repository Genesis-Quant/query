"""按需读取会话内查询结果，区分自有和借用连接。"""

import json
from typing import Any

from query.utils import SessionResult, logger


class QueryResult(SessionResult):
    def __init__(
        self,
        *,
        session: Any,
        source_ref: str,
        computed_ref: str,
        filtered_ref: str,
        data_ref: str,
        calendar_ref: str,
        owns_session: bool,
    ) -> None:
        super().__init__(session=session)
        self.source_ref = source_ref
        self.computed_ref = computed_ref
        self.filtered_ref = filtered_ref
        self.data_ref = data_ref
        self.calendar_ref = calendar_ref
        self.owns_session = owns_session

    @property
    def source_data(self):
        return self.download(self.source_ref)

    @property
    def computed_data(self):
        return self.download(self.computed_ref)

    @property
    def filtered_data(self):
        return self.download(self.filtered_ref)

    @property
    def data(self):
        return self.download(self.data_ref)

    @property
    def calendar(self):
        return self.download(self.calendar_ref)

    def close(self) -> None:
        if self.closed:
            return
        try:
            if self.owns_session:
                self.session.close()
            else:
                names = (self.source_ref, self.computed_ref, self.filtered_ref, self.data_ref, self.calendar_ref)
                self.session.run("\n".join(
                    f"if ({json.dumps(name)} in objs(true).name) undef({json.dumps(name)}, VAR)"
                    for name in names
                ) + "\nNULL")
        finally:
            self.closed = True

    def __exit__(self, exception_type, exception, traceback) -> bool:
        try:
            self.close()
        except Exception as error:
            if exception_type is None:
                raise
            logger.warning(f"异常退出时关闭查询结果失败：{type(error).__name__}")
        return False
