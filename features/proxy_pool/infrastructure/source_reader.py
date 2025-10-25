from __future__ import annotations

from pathlib import Path
from typing import List

from features.proxy_pool.application.ports import SubscriptionSource


class FileSubscriptionSource(SubscriptionSource):
    def __init__(self, file_path: Path):
        self._file_path = file_path

    def load(self) -> List[str]:
        if not self._file_path.exists():
            return []
        urls: List[str] = []
        for raw in self._file_path.read_text(encoding='utf-8').splitlines():
            stripped = raw.strip()
            if stripped and not stripped.startswith('#'):
                urls.append(stripped)
        return urls

