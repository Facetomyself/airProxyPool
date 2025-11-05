from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List

import yaml

from features.proxy_pool.application.ports import ProxyCollector
from features.proxy_pool.domain.models import Proxy

from .clash_parser import parse_config as clash_parse_to_forwards
from .parser import parse_forwards


class SubscriptionProxyCollector(ProxyCollector):
    """Collects subscription data and converts it into Proxy entities."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._root = project_root or Path.cwd()

    def collect(self) -> List[Proxy]:
        forward_lines = self._collect_forward_lines()
        return parse_forwards(forward_lines)

    def _collect_forward_lines(self) -> List[str]:
        collector_root = self._root / "features" / "subscription_collector"
        collector_path = collector_root / "subscribe" / "collect.py"
        clash_yaml_path = collector_root / "data" / "clash.yaml"

        if not collector_path.exists():
            raise FileNotFoundError(f"collector missing: {collector_path}")

        clash_yaml_path.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run([sys.executable, str(collector_path), "-s"], check=True)

        if not clash_yaml_path.exists():
            raise FileNotFoundError(f"clash.yaml missing: {clash_yaml_path}")

        data = yaml.safe_load(clash_yaml_path.read_text(encoding="utf-8")) or {}
        proxies = data.get("proxies", [])
        forward_content = clash_parse_to_forwards(proxies)
        return [ln for ln in forward_content.splitlines() if ln.strip()]
