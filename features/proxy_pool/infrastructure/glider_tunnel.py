from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from features.proxy_pool.application.ports import TunnelProcess
from features.proxy_pool.domain.subscriptions import GliderConfig


@dataclass
class GliderTunnelProcess(TunnelProcess):
    glider_path: Path
    config_path: Path

    def __post_init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._ensure_executable()

    def start(self, config: GliderConfig) -> None:
        self._launch()

    def restart(self, config: GliderConfig) -> None:
        self._stop_current()
        self._launch()

    def stop(self) -> None:
        self._stop_current()

    def _launch(self):
        if self._proc is not None:
            return
        if not self.config_path.exists():
            raise FileNotFoundError(f"glider config not found at {self.config_path}")
        self._proc = subprocess.Popen([str(self.glider_path), '-config', str(self.config_path)])

    def _stop_current(self):
        if not self._proc:
            return
        try:
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        except Exception:
            pass
        finally:
            self._proc = None

    def _ensure_executable(self):
        if not self.glider_path.exists():
            raise FileNotFoundError(f"glider executable not found at {self.glider_path}")
        try:
            self.glider_path.chmod(0o755)
        except Exception:
            pass
