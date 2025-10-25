from __future__ import annotations

from typing import Iterable, List, Protocol

from features.proxy_pool.domain.subscriptions import (
    FetchedContent,
    ForwardNode,
    GliderConfig,
    SchedulerConfig,
    SyncResult,
)


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
