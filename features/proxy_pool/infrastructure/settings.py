from __future__ import annotations

import os
from pathlib import Path
from typing import Final


ENV_FILE: Final[Path] = Path(".env")
DEFAULT_GLIDER_HTTP_PORT: Final[str] = "10707"
DEFAULT_GLIDER_ALT_PORT: Final[str] = "10710"
DEFAULT_SCORE_THRESHOLD: Final[float] = 60.0
DEFAULT_GLIDER_MAX_PUBLISH: Final[int] = 200


def _load_env_file() -> None:
    """Populate os.environ from .env if present without overriding existing values."""

    if not ENV_FILE.exists():
        return

    try:
        with ENV_FILE.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if not key:
                    continue

                if "#" in value:
                    value = value.split("#", 1)[0].strip()

                if key not in os.environ:
                    os.environ[key] = value
    except OSError:
        # If the file cannot be read we simply rely on existing environment configuration.
        return


def _normalise_listen(value: str, fallback_port: str) -> str:
    candidate = value.strip()
    if not candidate:
        candidate = fallback_port

    if candidate.startswith(":"):
        return candidate

    if ":" in candidate:
        return candidate

    return f":{candidate}"


_load_env_file()


def glider_http_listen() -> str:
    raw = os.getenv("GLIDER_HTTP_PORT", DEFAULT_GLIDER_HTTP_PORT)
    return _normalise_listen(raw, DEFAULT_GLIDER_HTTP_PORT)


def glider_alt_listen() -> str:
    raw = os.getenv("GLIDER_ALT_PORT", DEFAULT_GLIDER_ALT_PORT)
    return _normalise_listen(raw, DEFAULT_GLIDER_ALT_PORT)


def glider_score_threshold() -> float:
    raw = os.getenv("GLIDER_SCORE_THRESHOLD")
    if raw is None:
        return DEFAULT_SCORE_THRESHOLD
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_SCORE_THRESHOLD
    return max(0.0, min(100.0, value))


def glider_max_publish() -> int:
    raw = os.getenv("GLIDER_MAX_PUBLISH")
    if raw is None:
        return DEFAULT_GLIDER_MAX_PUBLISH
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_GLIDER_MAX_PUBLISH
    return max(0, value)
