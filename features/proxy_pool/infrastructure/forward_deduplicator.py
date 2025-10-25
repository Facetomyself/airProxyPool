from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, List

from features.proxy_pool.application.ports import ForwardDeduplicator
from features.proxy_pool.domain.subscriptions import ForwardNode


class ForwardLineDeduplicator(ForwardDeduplicator):
    """Deduplicate forward nodes while preserving original order."""

    def deduplicate(self, nodes: Iterable[ForwardNode]) -> List[ForwardNode]:
        seen = OrderedDict()
        for node in nodes:
            if not node.raw.startswith("forward="):
                continue
            if node.raw not in seen:
                seen[node.raw] = node
        return list(seen.values())

