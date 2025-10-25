from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

from celery import Celery

from ..application import services
from ..infrastructure.healthcheck import check_forward
from ..infrastructure.repository import ProxyRepository
from ..infrastructure.collector_runner import run_collect_and_update_glider


broker_url = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

app = Celery("airproxypool", broker=broker_url, backend=result_backend)
app.conf.timezone = "UTC"
app.conf.beat_schedule = {
    "fetch-proxies": {
        "task": "features.proxy_pool.infrastructure.tasks.fetch_proxies",
        "schedule": int(os.environ.get("FETCH_INTERVAL", "3600")),
    },
    "health-check": {
        "task": "features.proxy_pool.infrastructure.tasks.health_check_all",
        "schedule": int(os.environ.get("HEALTHCHECK_INTERVAL", "1800")),
    },
}


@app.task(name="features.proxy_pool.infrastructure.tasks.fetch_proxies")
def fetch_proxies() -> int:
    try:
        run_collect_and_update_glider(Path(os.getcwd()))
    except Exception:
        # keep going to try upsert from existing conf
        pass
    return services.upsert_proxies_from_conf()


@app.task(name="features.proxy_pool.infrastructure.tasks.health_check_all")
def health_check_all() -> int:
    # Load proxies and test via temporary glider
    # Prefer system-installed glider, fallback to project path
    glider_bin = Path(os.environ.get("GLIDER_BIN", "/usr/local/bin/glider"))
    if not glider_bin.exists():
        glider_bin = Path(os.getcwd()) / "glider" / ("glider.exe" if os.name == "nt" else "glider")
    if not glider_bin.exists():
        return 0
    try:
        glider_bin.chmod(0o755)
    except Exception:
        pass
    services.bootstrap()
    repo = ProxyRepository()
    proxies = repo.list(min_score=0.0, limit=500)
    repo.close()
    if not proxies:
        return 0
    total = 0
    def _f(idx: int, uri: str) -> tuple[str, bool, float | None]:
        ok, latency = check_forward(glider_bin, f"forward={uri}", 18081 + (idx % 2000))
        return uri, ok, latency

    repo2 = ProxyRepository()
    try:
        with ThreadPoolExecutor(max_workers=int(os.environ.get("HEALTHCHECK_WORKERS", "10"))) as ex:
            futures = {ex.submit(_f, i, p.uri): p.uri for i, p in enumerate(proxies)}
            for fut in as_completed(futures):
                uri, ok, latency = fut.result()
                repo2.update_health(uri, ok, latency if ok else None)
                total += 1
    finally:
        repo2.close()
    return total
