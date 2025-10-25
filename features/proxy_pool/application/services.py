from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import List, Optional

from ..domain.models import Proxy
from ..infrastructure.db import init_db
from ..infrastructure.repository import ProxyRepository
from ..infrastructure.parser import parse_forwards
from ..infrastructure.redis_state import incr_token_count


def bootstrap() -> None:
    init_db()


def load_proxies_from_glider_conf(conf_path: Path) -> List[Proxy]:
    if not conf_path.exists():
        return []
    lines = []
    with open(conf_path, "r", encoding="utf-8") as f:
        for ln in f.readlines():
            if ln.strip().startswith("forward="):
                lines.append(ln.strip())
    return parse_forwards(lines)


def upsert_proxies_from_conf() -> int:
    conf_path = Path(os.getcwd()) / "glider" / "glider.conf"
    proxies = load_proxies_from_glider_conf(conf_path)
    if not proxies:
        return 0
    repo = ProxyRepository()
    try:
        return repo.upsert_many(proxies)
    finally:
        repo.close()


def list_proxies(min_score: float = 0.0, limit: int = 200) -> List[Proxy]:
    repo = ProxyRepository()
    try:
        return repo.list(min_score=min_score, limit=limit)
    finally:
        repo.close()


def _deterministic_pick(candidates: List[Proxy], token: str, rotate_step: int) -> Proxy:
    key = f"{token}:{rotate_step}".encode("utf-8")
    h = hashlib.sha256(key).digest()
    idx = int.from_bytes(h[:4], "big") % max(1, len(candidates))
    return candidates[idx]


def get_rotated_proxy(token: str, rotate_every: int, min_score: float = 20.0) -> Optional[Proxy]:
    if rotate_every <= 0:
        rotate_every = 1
    count = incr_token_count(token)
    rotate_step = (count - 1) // rotate_every
    candidates = list_proxies(min_score=min_score, limit=200)
    if not candidates:
        return None
    return _deterministic_pick(candidates, token, rotate_step)

