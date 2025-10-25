from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional

import requests


TEST_URL = "http://www.msftconnecttest.com/connecttest.txt"
TIMEOUT = 8
TEST_LISTEN_HOST = "127.0.0.1"


def _write_temp_cfg(glider_path: Path, forward_line: str, port: int) -> Path:
    base = f"# Verbose mode, print logs\nverbose=false\nlisten={TEST_LISTEN_HOST}:{port}\nstrategy=rr\ncheck={TEST_URL}#expect=200\ncheckinterval=60\n\n"
    cfg_path = glider_path.parent / f"glider.health.{port}.conf"
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(base)
        if not forward_line.endswith("\n"):
            forward_line += "\n"
        f.write(forward_line)
    return cfg_path


def check_forward(glider_bin: Path, forward_line: str, port: int) -> tuple[bool, Optional[float]]:
    proc = None
    cfg = _write_temp_cfg(glider_bin, forward_line, port)
    try:
        proc = subprocess.Popen([str(glider_bin), "-config", str(cfg)], stdout=None, stderr=None, universal_newlines=True)
        time.sleep(0.5)
        proxies = {
            "http": f"http://{TEST_LISTEN_HOST}:{port}",
            "https": f"http://{TEST_LISTEN_HOST}:{port}",
        }
        start = time.time()
        resp = requests.get(TEST_URL, timeout=TIMEOUT, proxies=proxies, verify=False)
        ok = resp.status_code in (200, 204)
        latency = (time.time() - start) * 1000.0
        return ok, latency if ok else None
    except Exception:
        return False, None
    finally:
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

