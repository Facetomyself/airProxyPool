from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from .clash_parser import parse_config as clash_parse_to_forwards
from .settings import glider_http_listen


BASE_CONFIG_TEMPLATE = """# Verbose mode, print logs
verbose=true

# 监听地址
listen={listen}

# Round Robin mode: rr
# High Availability mode: ha
strategy=rr

# forwarder health check disabled (handled by external tester)
checkinterval=0

"""


def _build_base_config() -> str:
    listen = glider_http_listen()
    return BASE_CONFIG_TEMPLATE.format(listen=listen)


def update_glider_conf(forward_content: str, glider_conf_path: Path) -> None:
    glider_conf_path.parent.mkdir(parents=True, exist_ok=True)
    base_config = _build_base_config()
    if forward_content and not forward_content.endswith("\n"):
        forward_content = f"{forward_content}\n"
    glider_conf_path.write_text(base_config + forward_content, encoding="utf-8")


def run_collect_and_update_glider(project_root: Path | None = None) -> int:
    """Run subscription collector to gather nodes, convert to forward lines, update glider.conf.
    Returns number of forward entries written.
    """
    root = project_root or Path.cwd()
    collector_root = root / "features" / "subscription_collector"
    collector_path = collector_root / "subscribe" / "collect.py"
    clash_yaml_path = collector_root / "data" / "clash.yaml"
    glider_conf_path = root / "glider" / "glider.conf"

    if not collector_path.exists():
        raise FileNotFoundError(f"collector missing: {collector_path}")

    clash_yaml_path.parent.mkdir(parents=True, exist_ok=True)

    # Run aggregator collect (silent stdout)
    subprocess.run([sys.executable, str(collector_path), "-s"], check=True)

    if not clash_yaml_path.exists():
        raise FileNotFoundError(f"clash.yaml missing: {clash_yaml_path}")

    data = yaml.safe_load(clash_yaml_path.read_text(encoding='utf-8')) or {}
    proxies = data.get('proxies', [])
    forward_content = clash_parse_to_forwards(proxies)
    update_glider_conf(forward_content, glider_conf_path)
    return len([ln for ln in forward_content.splitlines() if ln.strip()])
