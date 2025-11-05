from __future__ import annotations

from pathlib import Path
from typing import List

from features.proxy_pool.application.ports import ProxyPublisher
from features.proxy_pool.domain.models import Proxy
from features.proxy_pool.domain.subscriptions import ForwardNode, GliderConfig

from .config_writer import FileConfigWriter
from .parser import format_forward_line
from .settings import glider_http_listen, glider_score_threshold


class GliderConfigPublisher(ProxyPublisher):
    """Publishes processed proxies to glider configuration output."""

    def __init__(self, output_path: Path, enable_healthcheck: bool = False, max_publish: int = 200) -> None:
        self._writer = FileConfigWriter(output_path)
        self._listen = glider_http_listen()
        self._threshold = glider_score_threshold()
        self._enable_healthcheck = enable_healthcheck
        self._max_publish = max_publish

    def publish(self, proxies: List[Proxy]) -> None:
        ordered = self._order_by_threshold(proxies)
        if self._max_publish > 0:
            ordered = ordered[: self._max_publish]
        nodes = [ForwardNode(raw=format_forward_line(proxy)) for proxy in ordered]
        config = GliderConfig(
            listen=self._listen,
            healthcheck_url="",
            forwards=nodes,
            healthcheck_enabled=self._enable_healthcheck,
        )
        self._writer.write(config)

    def _order_by_threshold(self, proxies: List[Proxy]) -> List[Proxy]:
        seen: set[str] = set()
        healthy: List[Proxy] = []
        for proxy in proxies:
            if proxy.uri in seen:
                continue
            if proxy.status != "up":
                continue
            if proxy.score < self._threshold:
                continue
            if not proxy.host:
                continue
            if proxy.scheme not in {"ss", "vmess"}:
                continue
            seen.add(proxy.uri)
            healthy.append(proxy)
        return healthy
