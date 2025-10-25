from __future__ import annotations

from pathlib import Path

from features.proxy_pool.application.ports import ConfigWriter
from features.proxy_pool.domain.subscriptions import GliderConfig


class FileConfigWriter(ConfigWriter):
    def __init__(self, path: Path):
        self._path = path

    def write(self, config: GliderConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(config.render(), encoding='utf-8')

