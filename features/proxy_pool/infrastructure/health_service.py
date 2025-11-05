from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

from features.proxy_pool.application.ports import ProxyHealthService, ProxyStoreFactory
from features.proxy_pool.domain.models import Proxy

from .healthcheck import check_forward
from .parser import format_forward_line


class GliderProxyHealthService(ProxyHealthService):
    """Evaluates proxies by spawning temporary glider instances and recording health metrics."""

    def __init__(
        self,
        store_factory: ProxyStoreFactory,
        *,
        worker_count: int | None = None,
        publish_limit: int = 10000,
        port_base: int = 18081,
        port_span: int = 2000,
    ) -> None:
        self._store_factory = store_factory
        self._worker_count = worker_count or int(os.environ.get("HEALTHCHECK_WORKERS", "10"))
        self._publish_limit = publish_limit
        self._port_base = port_base
        self._port_span = port_span

    def evaluate(self) -> List[Proxy]:
        glider_bin = self._resolve_glider_binary()
        if glider_bin is None:
            return []

        proxies = self._load_candidates()
        if not proxies:
            return []

        results = self._run_checks(glider_bin, proxies)
        self._record_results(results)
        return self._load_candidates(limit=self._publish_limit)

    def _resolve_glider_binary(self) -> Path | None:
        candidate = Path(os.environ.get("GLIDER_BIN", "/usr/local/bin/glider"))
        if not candidate.exists():
            exe_name = "glider.exe" if os.name == "nt" else "glider"
            candidate = Path(os.getcwd()) / "glider" / exe_name
            if not candidate.exists():
                return None
        try:
            candidate.chmod(0o755)
        except Exception:
            pass
        return candidate

    def _load_candidates(self, limit: int | None = None) -> List[Proxy]:
        effective_limit = limit or self._publish_limit
        store = self._store_factory()
        try:
            return store.list(min_score=0.0, limit=effective_limit)
        finally:
            store.close()

    def _run_checks(self, glider_bin: Path, proxies: List[Proxy]) -> List[Tuple[str, bool, float | None]]:
        results: List[Tuple[str, bool, float | None]] = []
        max_workers = max(1, self._worker_count)

        def _run(idx: int, proxy: Proxy) -> Tuple[str, bool, float | None]:
            forward_line = format_forward_line(proxy)
            port = self._port_base + (idx % self._port_span)
            ok, latency = check_forward(glider_bin, forward_line, port)
            return proxy.uri, ok, latency

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_run, idx, proxy): proxy.uri for idx, proxy in enumerate(proxies)}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    uri = futures[future]
                    results.append((uri, False, None))
        return results

    def _record_results(self, results: List[Tuple[str, bool, float | None]]) -> None:
        if not results:
            return
        store = self._store_factory()
        try:
            for uri, ok, latency in results:
                store.update_health(uri, ok, latency if ok else None)
        finally:
            store.close()
