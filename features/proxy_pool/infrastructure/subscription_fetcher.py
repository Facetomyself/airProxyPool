from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

try:
    import requests
except ImportError as exc:  # pragma: no cover - configuration issue
    raise RuntimeError("requests package is required for subscription fetching") from exc

from features.proxy_pool.application.ports import SubscriptionFetcher
from features.proxy_pool.domain.subscriptions import FetchedContent


@dataclass
class RequestsSubscriptionFetcher(SubscriptionFetcher):
    timeout: int = 30
    verify_tls: bool = False
    headers: Optional[Dict[str, str]] = None

    def __post_init__(self):
        self._session = requests.Session()
        if not self.verify_tls:
            self._session.verify = False
            requests.packages.urllib3.disable_warnings()  # type: ignore[attr-defined]

    def fetch(self, url: str) -> FetchedContent:
        response = self._session.get(url, timeout=self.timeout, headers=self.headers)
        response.raise_for_status()
        return FetchedContent(
            url=url,
            text=response.text,
            content_type=response.headers.get("Content-Type"),
        )
