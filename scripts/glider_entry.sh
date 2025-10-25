#!/bin/sh
set -eu

GLIDER_BIN="${GLIDER_BIN:-/usr/local/bin/glider}"
GLIDER_CONFIG="${GLIDER_CONFIG:-/config/glider.conf}"
RELOAD_INTERVAL="${RELOAD_INTERVAL:-30}"

echo "[glider-entry] bin=$GLIDER_BIN config=$GLIDER_CONFIG interval=$RELOAD_INTERVAL"

cfg_dir=$(dirname "$GLIDER_CONFIG")
mkdir -p "$cfg_dir"

while :; do
  if [ ! -f "$GLIDER_CONFIG" ]; then
    echo "[glider-entry] waiting for config $GLIDER_CONFIG ..."
    sleep 5
    continue
  fi

  if [ ! -x "$GLIDER_BIN" ]; then
    echo "[glider-entry] WARN: glider binary not executable: $GLIDER_BIN"
    chmod +x "$GLIDER_BIN" || true
  fi

  sum=$(md5sum "$GLIDER_CONFIG" | awk '{print $1}')
  echo "[glider-entry] starting glider with checksum=$sum"
  "$GLIDER_BIN" -config "$GLIDER_CONFIG" &
  pid=$!

  while kill -0 "$pid" 2>/dev/null; do
    sleep "$RELOAD_INTERVAL"
    if [ ! -f "$GLIDER_CONFIG" ]; then
      echo "[glider-entry] config removed, restarting"
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      break
    fi
    new=$(md5sum "$GLIDER_CONFIG" | awk '{print $1}')
    if [ "$new" != "$sum" ]; then
      echo "[glider-entry] config changed ($sum -> $new), restarting"
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      break
    fi
  done
done
