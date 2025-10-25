#!/usr/bin/env bash
set -euo pipefail

# Simple entry orchestrator for API service
# Usage: ./main.sh api|worker|beat

ROLE=${1:-api}

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Default envs
: "${APP_HOST:=0.0.0.0}"
: "${APP_PORT:=8000}"
: "${WORKERS:=1}"
: "${LOG_LEVEL:=info}"

# Celery
: "${CELERY_CONCURRENCY:=4}"
: "${CELERY_BROKER_URL:=redis://redis:6379/0}"
: "${CELERY_RESULT_BACKEND:=redis://redis:6379/1}"

# Ensure glider binary is executable if present
if [ -f "glider/glider" ]; then
  chmod +x glider/glider || true
fi

case "$ROLE" in
  api)
    exec uvicorn app:app --host "$APP_HOST" --port "$APP_PORT" --workers "$WORKERS" --log-level "$LOG_LEVEL"
    ;;
  worker)
    exec celery -A features.proxy_pool.infrastructure.tasks.app worker --loglevel=INFO --concurrency "$CELERY_CONCURRENCY"
    ;;
  beat)
    exec celery -A features.proxy_pool.infrastructure.tasks.app beat --loglevel=INFO
    ;;
  *)
    echo "ERROR: Unknown role '$ROLE'. Use api|worker|beat" >&2
    exit 1
    ;;
esac

