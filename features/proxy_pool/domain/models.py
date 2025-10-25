from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Proxy:
    id: Optional[int]
    uri: str
    scheme: str
    host: str
    port: int
    label: Optional[str] = None
    status: str = "unknown"  # unknown|up|down
    score: float = 50.0
    success_count: int = 0
    fail_count: int = 0
    avg_latency_ms: float = -1.0
    last_checked: Optional[datetime] = None
    last_ok: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

