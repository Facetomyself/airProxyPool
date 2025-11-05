from __future__ import annotations

from pathlib import Path
from features.proxy_pool.application.orchestrator import ProxyPoolOrchestrator
from features.proxy_pool.application.ports import ProxyStoreFactory

from .collector_runner import SubscriptionProxyCollector
from .glider_publisher import GliderConfigPublisher
from .health_service import GliderProxyHealthService
from .repository import ProxyRepository
from .settings import glider_max_publish


def _store_factory() -> ProxyRepository:
    return ProxyRepository()


def build_proxy_pool_orchestrator(
    *,
    project_root: Path | None = None,
    glider_conf_path: Path | None = None,
) -> ProxyPoolOrchestrator:
    root = project_root or Path.cwd()
    output_path = glider_conf_path or (root / "glider" / "glider.conf")

    collector = SubscriptionProxyCollector(project_root=root)
    store_factory: ProxyStoreFactory = _store_factory
    health_service = GliderProxyHealthService(store_factory)
    publisher = GliderConfigPublisher(output_path, max_publish=glider_max_publish())

    return ProxyPoolOrchestrator(
        collector=collector,
        store_factory=store_factory,
        health_service=health_service,
        publisher=publisher,
    )
