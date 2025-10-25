FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends bash curl ca-certificates tar \
    && rm -rf /var/lib/apt/lists/*

# Optional pip mirror for slow networks
ARG PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_NO_CACHE_DIR=1

# Copy project files
COPY pyproject.toml README.md ./
COPY subscriptions.txt ./
COPY features features
COPY app.py main.sh ./
COPY scripts scripts

# Install deps
ARG WITH_GLIDER="false"
ARG GLIDER_VERSION="0.16.3"
RUN python -m pip install --no-cache-dir fastapi uvicorn[standard] celery redis sqlalchemy requests \
    && python -m pip install --no-cache-dir -r features/subscription_collector/requirements.txt \
    && if [ "$WITH_GLIDER" = "true" ]; then \
         curl -fsSL -o /tmp/glider.tgz https://github.com/nadoo/glider/releases/download/v${GLIDER_VERSION}/glider_${GLIDER_VERSION}_linux_amd64.tar.gz && \
         tar -xzf /tmp/glider.tgz -C /tmp && \
         mv /tmp/glider_${GLIDER_VERSION}_linux_amd64/glider /usr/local/bin/glider && \
         chmod +x /usr/local/bin/glider && \
         rm -rf /tmp/glider.tgz /tmp/glider_${GLIDER_VERSION}_linux_amd64; \
       fi

# Ensure scripts are executable regardless of pip step cache/results
RUN chmod +x /app/main.sh || true \
    && chmod +x /app/scripts/glider_entry.sh || true

EXPOSE 8000

CMD ["/app/main.sh", "api"]
