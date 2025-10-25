from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime

from features.proxy_pool.application.ports import (
    ConfigWriter,
    SubscriptionSource,
    TunnelProcess,
)
from features.proxy_pool.application.subscription_service import SubscriptionSyncService
from features.proxy_pool.domain.subscriptions import ForwardNode, GliderConfig, SchedulerConfig, SyncResult


@dataclass
class SubscriptionScheduler:
    source: SubscriptionSource
    sync_service: SubscriptionSyncService
    tunnel: TunnelProcess
    config_writer: ConfigWriter
    _started: bool = field(init=False, default=False)
    _last_hash: str | None = field(init=False, default=None)

    def run(self, config: SchedulerConfig) -> None:
        self._ensure_urls_available(config)
        result = self.sync_and_apply(config)
        if config.dry_run or config.run_once:
            return
        if result is None or not result.forwards:
            raise RuntimeError("No usable forwards on initial sync")

        while True:
            time.sleep(config.interval_seconds)
            refreshed = self.sync_and_apply(config)
            if not refreshed or not refreshed.forwards:
                print(f"[{datetime.now()}] No usable entries; keeping current glider process and config.")
                continue

    def sync_and_apply(self, config: SchedulerConfig) -> SyncResult | None:
        result = self._sync_once(config)
        if not result or not result.forwards:
            return result
        new_hash = self._hash_forwards(result.forwards)
        if config.dry_run:
            return result
        if self._last_hash is not None and new_hash == self._last_hash:
            print(f"[{datetime.now()}] Entries unchanged; no restart needed.")
            return result
        glider_config = GliderConfig(
            listen=config.listen,
            healthcheck_url=config.healthcheck_url,
            forwards=result.forwards,
            healthcheck_enabled=False,
        )
        self.config_writer.write(glider_config)
        if not self._started:
            self.tunnel.start(glider_config)
            self._started = True
            print(f"[{datetime.now()}] Glider started with {len(result.forwards)} entries.")
        else:
            self.tunnel.restart(glider_config)
            print(f"[{datetime.now()}] Glider restarted with updated config.")
        self._last_hash = new_hash
        return result

    def _ensure_urls_available(self, config: SchedulerConfig) -> None:
        urls = self.source.load()
        if not urls:
            raise RuntimeError(f"No subscriptions found in {config.subscriptions_file}")

    def _sync_once(self, config: SchedulerConfig) -> SyncResult | None:
        urls = self.source.load()
        if not urls:
            print(f"[{datetime.now()}] No subscriptions found; skipping update.")
            return None
        result = self.sync_service.sync(urls)
        now = datetime.now()
        print(
            f"[{now}] Fetched subscriptions: ok={result.stats.ok_urls}, "
            f"failed={result.stats.failed_urls}, entries={result.stats.entries}"
        )
        return result

    def _hash_forwards(self, forwards: list[ForwardNode]) -> str:
        digest = hashlib.sha256()
        for node in forwards:
            digest.update(node.raw.encode('utf-8'))
        return digest.hexdigest()
