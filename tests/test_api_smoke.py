import os
import types
from fastapi.testclient import TestClient

import app as app_module


def test_healthz():
    client = TestClient(app_module.app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

