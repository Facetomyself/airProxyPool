from __future__ import annotations

import os
import json
from typing import Optional

import redis


def redis_client() -> redis.Redis:
    url = os.environ.get("REDIS_URL", os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    return redis.from_url(url)


def incr_token_count(token: str, ttl: int = 86400) -> int:
    r = redis_client()
    key = f"proxypool:token:{token}:count"
    cnt = r.incr(key)
    if cnt == 1:
        r.expire(key, ttl)
    return int(cnt)

