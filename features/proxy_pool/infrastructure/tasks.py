from __future__ import annotations

import os
from pathlib import Path

from celery import Celery

from features.proxy_pool.application.orchestrator import ProxyPoolOrchestrator

from ..application import services
from .orchestrator_factory import build_proxy_pool_orchestrator


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


def _orchestrator() -> ProxyPoolOrchestrator:
    services.bootstrap()
    project_root = Path(os.getcwd())
    return build_proxy_pool_orchestrator(project_root=project_root)


@app.task(name="features.proxy_pool.infrastructure.tasks.fetch_proxies")
def fetch_proxies() -> int:
    orchestrator = _orchestrator()
    try:
        result = orchestrator.refresh_pool()
    except Exception:
        orchestrator.perform_maintenance()
        return 0
    return result.stored


@app.task(name="features.proxy_pool.infrastructure.tasks.health_check_all")
def health_check_all() -> int:
    orchestrator = _orchestrator()
    return orchestrator.perform_maintenance()
