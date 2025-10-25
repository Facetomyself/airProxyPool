from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from features.proxy_pool.application.ports import (
    ForwardDeduplicator,
    ForwardTester,
    ParserStrategy,
    SubscriptionFetcher,
)
from features.proxy_pool.domain.subscriptions import (
    FetchedContent,
    ForwardNode,
    SubscriptionSyncStats,
    SyncResult,
)


@dataclass
class SubscriptionSyncService:
    fetcher: SubscriptionFetcher
    parsers: Iterable[ParserStrategy]
    deduplicator: ForwardDeduplicator
    tester: ForwardTester

    def sync(self, urls: Iterable[str]) -> SyncResult:
        url_list = list(urls)
        stats = SubscriptionSyncStats.create(url_list)
        collected: List[ForwardNode] = []

        for url in url_list:
            try:
                content = self.fetcher.fetch(url)
                parser = self._locate_parser(content)
                if parser is None:
                    stats.record_failure(url, "no parser available")
                    continue
                nodes = parser.parse(content)
                if not nodes:
                    stats.record_failure(url, "no usable nodes")
                    continue
                collected.extend(nodes)
                stats.record_success(url, len(nodes), parser.name)
            except Exception as exc:  # pylint: disable=broad-except
                stats.record_failure(url, str(exc))

        deduped = self.deduplicator.deduplicate(collected)
        tested = self.tester.filter_usable(deduped)
        stats.entries = len(tested)
        return SyncResult(stats=stats, forwards=tested)

    def _locate_parser(self, content: FetchedContent) -> ParserStrategy | None:
        for parser in self.parsers:
            if parser.supports(content):
                return parser
        return None
