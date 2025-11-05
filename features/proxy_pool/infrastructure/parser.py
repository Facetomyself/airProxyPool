from __future__ import annotations

import re
from typing import Iterable, List

from ..domain.models import Proxy


_FORWARD_RE = re.compile(r"^forward=(?P<uri>(?P<scheme>ss|vmess)://[^#\s]+)(?:#(?P<label>.*))?$")


def parse_forwards(lines: Iterable[str]) -> List[Proxy]:
    proxies: List[Proxy] = []
    for raw in lines:
        line = raw.strip()
        if not line or not line.startswith("forward="):
            continue
        m = _FORWARD_RE.match(line)
        if not m:
            continue
        uri = m.group("uri")
        scheme = m.group("scheme")
        host, port = _extract_host_port(uri)
        proxies.append(Proxy(id=None, uri=uri, scheme=scheme, host=host, port=port, label=m.group("label") or None))
    return proxies


def format_forward_line(proxy: Proxy) -> str:
    suffix = f"#{proxy.label}" if proxy.label else ""
    return f"forward={proxy.uri}{suffix}"


def _extract_host_port(uri: str) -> tuple[str, int]:
    # ss://METHOD:PASSWORD@host:port...
    # vmess://none:UUID@host:port?alterID=...
    try:
        right = uri.split("@", 1)[1]
        host_port = right.split("/", 1)[0]
        host, port_s = host_port.split(":", 1)
        # Trim query/hash remnants from port portion
        port_s = port_s.split("?", 1)[0].split("#", 1)[0]
        return host, int(port_s)
    except Exception:
        return "", 0
