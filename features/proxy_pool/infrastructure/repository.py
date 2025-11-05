from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert

from .db import ProxyORM, SessionLocal
from ..domain.models import Proxy


class ProxyRepository:
    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session or SessionLocal()

    def __enter__(self) -> ProxyRepository:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._session.close()

    def upsert_many(self, proxies: Sequence[Proxy]) -> int:
        if not proxies:
            return 0
        count = 0
        for p in proxies:
            stmt = (
                insert(ProxyORM)
                .values(
                    uri=p.uri,
                    scheme=p.scheme,
                    host=p.host,
                    port=p.port,
                    label=p.label,
                )
                .on_conflict_do_update(
                    index_elements=[ProxyORM.uri],
                    set_={
                        "scheme": p.scheme,
                        "host": p.host,
                        "port": p.port,
                        "label": p.label,
                        "updated_at": datetime.utcnow(),
                    },
                )
            )
            self._session.execute(stmt)
            count += 1
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            raise
        return count

    def list(self, min_score: float = 0.0, limit: int = 200) -> List[Proxy]:
        rows = self._session.execute(
            select(ProxyORM).where(ProxyORM.score >= min_score).order_by(ProxyORM.score.desc(), ProxyORM.id.asc()).limit(limit)
        ).scalars().all()
        return [self._to_domain(x) for x in rows]

    def get_by_uri(self, uri: str) -> Optional[Proxy]:
        row = self._session.execute(select(ProxyORM).where(ProxyORM.uri == uri)).scalar_one_or_none()
        return self._to_domain(row) if row else None

    def update_health(self, uri: str, ok: bool, latency_ms: Optional[float]) -> None:
        row = self._session.execute(select(ProxyORM).where(ProxyORM.uri == uri)).scalar_one_or_none()
        if not row:
            return
        if ok:
            row.success_count += 1
            row.status = "up"
            row.last_ok = datetime.utcnow()
            # latency EMA
            if latency_ms is not None and latency_ms >= 0:
                if row.avg_latency_ms < 0:
                    row.avg_latency_ms = latency_ms
                else:
                    row.avg_latency_ms = 0.6 * row.avg_latency_ms + 0.4 * latency_ms
        else:
            row.fail_count += 1
            # if many fails, mark down
            row.status = "down" if row.fail_count > 3 and row.success_count == 0 else row.status
        row.last_checked = datetime.utcnow()
        # score: success ratio minus latency factor
        total = max(1, row.success_count + row.fail_count)
        success_ratio = row.success_count / total
        latency_penalty = 0.0
        if row.avg_latency_ms >= 0:
            latency_penalty = min(0.7, row.avg_latency_ms / 3000.0)  # cap penalty
        score = max(0.0, min(100.0, 100.0 * (success_ratio * (1.0 - latency_penalty))))
        row.score = score
        self._session.commit()

    def _to_domain(self, orm: ProxyORM) -> Proxy:
        return Proxy(
            id=orm.id,
            uri=orm.uri,
            scheme=orm.scheme,
            host=orm.host,
            port=orm.port,
            label=orm.label,
            status=orm.status,
            score=orm.score,
            success_count=orm.success_count,
            fail_count=orm.fail_count,
            avg_latency_ms=orm.avg_latency_ms,
            last_checked=orm.last_checked,
            last_ok=orm.last_ok,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
