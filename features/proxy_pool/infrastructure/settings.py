from __future__ import annotations

import os
from pathlib import Path
from typing import Final


ENV_FILE: Final[Path] = Path(".env")
DEFAULT_GLIDER_HTTP_PORT: Final[str] = "10707"
DEFAULT_GLIDER_ALT_PORT: Final[str] = "10710"


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
