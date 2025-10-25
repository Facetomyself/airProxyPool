from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

from features.proxy_pool.application.subscription_scheduler import SubscriptionScheduler
from features.proxy_pool.application.subscription_service import SubscriptionSyncService
from features.proxy_pool.domain.subscriptions import SchedulerConfig
from features.proxy_pool.infrastructure.config_writer import FileConfigWriter
from features.proxy_pool.infrastructure.forward_deduplicator import ForwardLineDeduplicator
from features.proxy_pool.infrastructure.forward_tester import GliderForwardTester
from features.proxy_pool.infrastructure.glider_tunnel import GliderTunnelProcess
from features.proxy_pool.infrastructure.source_reader import FileSubscriptionSource
from features.proxy_pool.infrastructure.subscription_fetcher import (
    RequestsSubscriptionFetcher,
)
from features.proxy_pool.infrastructure.subscription_parsers import (
    ClashYamlParser,
    TextSubscriptionParser,
)

SUBSCRIPTIONS_FILE = 'subscriptions.txt'
CONFIG_OUTPUT = str(Path('glider') / 'glider.conf')
LISTEN = ':10710'
INTERVAL_SECONDS = 6000
GLIDER_BINARY = str(Path('glider') / ('glider.exe' if os.name == 'nt' else 'glider'))
RUN_ONCE = False
DRY_RUN = False
TEST_EACH_FORWARD = True
TEST_URL = 'http://www.msftconnecttest.com/connecttest.txt#expect=200'
TEST_EXPECT_STATUSES = (204, 200)
TEST_TIMEOUT = 8
TEST_LISTEN_HOST = '127.0.0.1'
TEST_START_PORT = 18081
TEST_MAX_WORKERS = 20
HEALTHCHECK_URL = 'http://www.msftconnecttest.com/connecttest.txt#expect=200'


def build_scheduler() -> tuple[SubscriptionScheduler, SchedulerConfig]:
    config_path = Path(CONFIG_OUTPUT)
    glider_path = Path(GLIDER_BINARY)
    settings = SchedulerConfig(
        subscriptions_file=Path(SUBSCRIPTIONS_FILE),
        listen=LISTEN,
        interval_seconds=INTERVAL_SECONDS,
        healthcheck_url=HEALTHCHECK_URL,
        config_output=config_path,
        run_once=RUN_ONCE,
        dry_run=DRY_RUN,
        tls_verify=False,
    )

    fetcher = RequestsSubscriptionFetcher(verify_tls=settings.tls_verify)
    parsers = [ClashYamlParser(), TextSubscriptionParser()]
    deduplicator = ForwardLineDeduplicator()
    tester = (
        GliderForwardTester(
            glider_path=glider_path,
            listen_host=TEST_LISTEN_HOST,
            start_port=TEST_START_PORT,
            timeout=TEST_TIMEOUT,
            max_workers=TEST_MAX_WORKERS,
            test_url=TEST_URL,
            expect_statuses=TEST_EXPECT_STATUSES,
        )
        if TEST_EACH_FORWARD
        else _NoopForwardTester()
    )
    sync_service = SubscriptionSyncService(
        fetcher=fetcher,
        parsers=parsers,
        deduplicator=deduplicator,
        tester=tester,
    )

    source = FileSubscriptionSource(Path(SUBSCRIPTIONS_FILE))
    config_writer = FileConfigWriter(config_path)
    tunnel = GliderTunnelProcess(glider_path=glider_path, config_path=config_path)
    scheduler = SubscriptionScheduler(
        source=source,
        sync_service=sync_service,
        tunnel=tunnel,
        config_writer=config_writer,
    )
    return scheduler, settings


class _NoopForwardTester:
    def filter_usable(self, nodes):
        return list(nodes)


def main():
    scheduler, settings = build_scheduler()

    def _cleanup(signum, frame):  # noqa: ARG001
        scheduler.tunnel.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)

    scheduler.run(settings)


if __name__ == '__main__':
    main()
