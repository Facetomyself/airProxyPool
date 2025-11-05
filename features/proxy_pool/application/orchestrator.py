from __future__ import annotations

from dataclasses import dataclass
from typing import List

from features.proxy_pool.domain.models import Proxy

from .ports import (
    ProxyCollector,
    ProxyHealthService,
    ProxyPublisher,
    ProxyStoreFactory,
)


@dataclass(frozen=True)
class ProxyPoolRefreshResult:
    collected: int
    stored: int
    published: int


class ProxyPoolOrchestrator:
    """Orchestrates the end-to-end lifecycle of the proxy pool."""

    def __init__(
        self,
        collector: ProxyCollector,
        store_factory: ProxyStoreFactory,
        health_service: ProxyHealthService,
        publisher: ProxyPublisher,
    ) -> None:
        self._collector = collector
        self._store_factory = store_factory
        self._health_service = health_service
        self._publisher = publisher

    def refresh_pool(self) -> ProxyPoolRefreshResult:
        """Collect, persist, evaluate, and publish proxies in a single pass."""
        collected_proxies = self._collector.collect()
        stored_count = self._persist(collected_proxies)
        evaluated = self._health_service.evaluate()
        published_count = self._publish(evaluated)
        return ProxyPoolRefreshResult(
            collected=len(collected_proxies),
            stored=stored_count,
            published=published_count,
        )

    def perform_maintenance(self) -> int:
        """Re-evaluate existing proxies and update downstream publisher."""
        evaluated = self._health_service.evaluate()
        self._publish(evaluated)
        return len(evaluated)

    def _persist(self, proxies: List[Proxy]) -> int:
        store = self._store_factory()
        try:
            return store.upsert_many(proxies)
        finally:
            store.close()

    def _publish(self, proxies: List[Proxy]) -> int:
        self._publisher.publish(proxies)
        return len(proxies)
