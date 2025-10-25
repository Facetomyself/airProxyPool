from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    create_engine,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker


DB_PATH = os.environ.get("PROXYPOOL_DB", os.path.join(os.getcwd(), "data.db"))
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class ProxyORM(Base):
    __tablename__ = "proxies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    uri = Column(String(2048), nullable=False, unique=True)
    scheme = Column(String(16), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    label = Column(String(255), nullable=True)
    status = Column(String(16), default="unknown", nullable=False)
    score = Column(Float, default=50.0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    fail_count = Column(Integer, default=0, nullable=False)
    avg_latency_ms = Column(Float, default=-1.0, nullable=False)
    last_checked = Column(DateTime, nullable=True)
    last_ok = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("uri", name="uq_proxy_uri"),
    )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

