import os

import pytest
import requests

from features.proxy_pool.infrastructure.settings import glider_http_listen


@pytest.mark.skipif(
    not os.getenv("RUN_PROXY_E2E"),
    reason="Requires running glider forwarder and external network access",
)
def test_proxy_forwarding_end_to_end():
    listen_addr = glider_http_listen()
    port = listen_addr.split(":")[-1]
    proxies = {"http": f"http://127.0.0.1:{port}", "https": f"http://127.0.0.1:{port}"}
    response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10)
    assert response.status_code == 200
