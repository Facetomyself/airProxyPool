from __future__ import annotations

from typing import Iterable, List, Protocol, Sequence, Callable, Optional

from features.proxy_pool.domain.subscriptions import (
    FetchedContent,
    ForwardNode,
    GliderConfig,
    SchedulerConfig,
    SyncResult,
)
from features.proxy_pool.domain.models import Proxy


class SubscriptionFetcher(Protocol):
    def fetch(self, url: str) -> FetchedContent:
        """Retrieve subscription payload from remote source."""


class ParserStrategy(Protocol):
    name: str

    def supports(self, content: FetchedContent) -> bool:
        """Return True if parser can handle fetched content."""

    def parse(self, content: FetchedContent) -> List[ForwardNode]:
        """Convert content into glider forward nodes."""


class ForwardDeduplicator(Protocol):
    def deduplicate(self, nodes: Iterable[ForwardNode]) -> List[ForwardNode]:
        """Remove duplicated forward nodes while preserving order."""


class ForwardTester(Protocol):
    def filter_usable(self, nodes: List[ForwardNode]) -> List[ForwardNode]:
        """Return subset of nodes that pass connectivity checks."""


class ConfigWriter(Protocol):
    def write(self, config: GliderConfig) -> None:
        """Persist glider configuration state."""


class TunnelProcess(Protocol):
    def start(self, config: GliderConfig) -> None:
        """Start tunnel process with given configuration."""

    def restart(self, config: GliderConfig) -> None:
        """Restart tunnel process with new configuration."""

    def stop(self) -> None:
        """Stop running tunnel process if any."""


class SubscriptionSource(Protocol):
    def load(self) -> List[str]:
        """Return list of subscription URLs."""


class SchedulerLifecycle(Protocol):
    def run(self, config: SchedulerConfig) -> None:
        """Execute scheduler loop until termination."""


class ProxyCollector(Protocol):
    def collect(self) -> List[Proxy]:
        """Return proxies sourced from subscriptions or other upstream feeds."""


class ProxyHealthService(Protocol):
    def evaluate(self) -> List[Proxy]:
        """Recalculate health metrics for stored proxies and return prioritized listing."""


class ProxyPublisher(Protocol):
    def publish(self, proxies: List[Proxy]) -> None:
        """Publish processed proxies to downstream consumers such as glider."""


class ProxyStore(Protocol):
    def upsert_many(self, proxies: Sequence[Proxy]) -> int:
        """Persist or update proxies."""

    def close(self) -> None:
        """Release underlying resources."""

    def list(self, min_score: float = 0.0, limit: int = 200) -> List[Proxy]:
        """Retrieve proxies ordered by score."""

    def update_health(self, uri: str, ok: bool, latency_ms: Optional[float]) -> None:
        """Persist health metrics for a single proxy."""


ProxyStoreFactory = Callable[[], ProxyStore]
