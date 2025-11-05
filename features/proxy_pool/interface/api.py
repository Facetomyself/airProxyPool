from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..application import services
from ..infrastructure.parser import _extract_host_port
from ..infrastructure.orchestrator_factory import build_proxy_pool_orchestrator


router = APIRouter()


class ProxyOut(BaseModel):
    uri: str
    scheme: str
    host: str
    port: int
    label: Optional[str]
    status: str
    score: float
    avg_latency_ms: float


@router.on_event("startup")
def on_startup():
    services.bootstrap()


@router.get("/proxies", response_model=List[ProxyOut])
def list_proxies(min_score: float = Query(0.0, ge=0.0, le=100.0), limit: int = Query(200, ge=1, le=1000)):
    items = services.list_proxies(min_score=min_score, limit=limit)
    out: List[ProxyOut] = []
    for p in items:
        host, port = (p.host, p.port)
        if (not host or port <= 0 or port > 65535) and p.uri:
            host, port = _extract_host_port(p.uri)
        out.append(
            ProxyOut(
                uri=p.uri,
                scheme=p.scheme,
                host=host,
                port=port,
                label=p.label,
                status=p.status,
                score=p.score,
                avg_latency_ms=p.avg_latency_ms,
            )
        )
    return out


class RotateOut(BaseModel):
    token: str
    rotate_every: int
    proxy: ProxyOut


@router.get("/proxy/rotate", response_model=RotateOut)
def get_rotated_proxy(token: str, rotate_every: int = Query(5, ge=1), min_score: float = Query(20.0, ge=0.0, le=100.0)):
    p = services.get_rotated_proxy(token=token, rotate_every=rotate_every, min_score=min_score)
    if not p:
        raise HTTPException(status_code=503, detail="No proxies available")
    host, port = (p.host, p.port)
    if (not host or port <= 0 or port > 65535) and p.uri:
        host, port = _extract_host_port(p.uri)
    return RotateOut(
        token=token,
        rotate_every=rotate_every,
        proxy=ProxyOut(
            uri=p.uri,
            scheme=p.scheme,
            host=host,
            port=port,
            label=p.label,
            status=p.status,
            score=p.score,
            avg_latency_ms=p.avg_latency_ms,
        ),
    )


class FetchResult(BaseModel):
    updated: int


@router.post("/proxies/fetch", response_model=FetchResult)
def fetch_now():
    project_root = Path(os.getcwd())
    orchestrator = build_proxy_pool_orchestrator(project_root=project_root)
    try:
        result = orchestrator.refresh_pool()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"collector failed: {e}")
    return FetchResult(updated=result.stored)
