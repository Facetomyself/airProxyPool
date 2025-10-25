from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class FetchedContent:
    url: str
    text: str
    content_type: Optional[str]


@dataclass(frozen=True)
class ForwardNode:
    raw: str

    def as_line(self) -> str:
        return self.raw if self.raw.endswith("\n") else f"{self.raw}\n"


@dataclass
class SubscriptionFetchStat:
    url: str
    count: int = 0
    error: Optional[str] = None
    format: Optional[str] = None


@dataclass
class SubscriptionSyncStats:
    total_urls: int
    ok_urls: int = 0
    failed_urls: int = 0
    entries: int = 0
    by_url: Dict[str, SubscriptionFetchStat] = field(default_factory=dict)

    @classmethod
    def create(cls, urls: Iterable[str]) -> "SubscriptionSyncStats":
        url_list = list(urls)
        stats = cls(total_urls=len(url_list))
        stats.by_url = {url: SubscriptionFetchStat(url=url) for url in url_list}
        return stats

    def record_success(self, url: str, count: int, fmt: Optional[str]):
        self.ok_urls += 1
        stat = self.by_url.setdefault(url, SubscriptionFetchStat(url=url))
        stat.count = count
        stat.format = fmt

    def record_failure(self, url: str, error: str):
        self.failed_urls += 1
        stat = self.by_url.setdefault(url, SubscriptionFetchStat(url=url))
        stat.error = error


@dataclass
class SchedulerConfig:
    subscriptions_file: Path
    listen: str
    interval_seconds: int
    healthcheck_url: str
    config_output: Path
    run_once: bool = False
    dry_run: bool = False
    tls_verify: bool = False


@dataclass(frozen=True)
class GliderConfig:
    listen: str
    healthcheck_url: str
    forwards: List[ForwardNode]
    healthcheck_enabled: bool = True

    def render(self) -> str:
        header_lines = [
            "# Verbose mode, print logs",
            "verbose=true",
            "",
            "# listen address",
            f"listen={self.listen}",
            "",
            "# strategy: rr (round-robin) or ha (high-availability)",
            "strategy=rr",
            "",
        ]
        if self.healthcheck_enabled and self.healthcheck_url:
            header_lines += [
                "# forwarder health check",
                f"check={self.healthcheck_url}",
                "",
                "# check interval(seconds)",
                "checkinterval=300",
                "",
            ]
        else:
            header_lines += [
                "# forwarder health check disabled",
                "checkinterval=0",
                "",
            ]
        header = "\n".join(header_lines) + "\n"
        body = "".join(node.as_line() for node in self.forwards)
        return header + body


@dataclass
class SyncResult:
    stats: SubscriptionSyncStats
    forwards: List[ForwardNode]
