from __future__ import annotations

import base64
import re
from typing import List

import yaml

from features.proxy_pool.application.ports import ParserStrategy
from features.proxy_pool.domain.subscriptions import FetchedContent, ForwardNode
from .clash_parser import parse_config as parse_clash_proxies


class TextSubscriptionParser(ParserStrategy):
    name = "plain-text"
    def supports(self, content: FetchedContent) -> bool:
        content_type = (content.content_type or "").lower()
        if "yaml" in content_type:
            return False
        head = self._first_line(content.text)
        return not head.startswith("proxies:")

    def parse(self, content: FetchedContent) -> List[ForwardNode]:
        decoded = self._maybe_decode_base64_blob(content.text)
        forwards = self._parse_lines(decoded)
        if not forwards:
            fallback = self._try_decode_full_blob(content.text)
            forwards = self._parse_lines(fallback)
        return [ForwardNode(raw=line) for line in forwards]

    def _first_line(self, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return ""

    def _maybe_decode_base64_blob(self, text: str) -> str:
        compact = ''.join(text.split())
        if not compact:
            return text
        if not re.fullmatch(r'[A-Za-z0-9+/=_-]+', compact):
            return text
        try:
            decoded = base64.b64decode(self._pad(compact))
            decoded_text = decoded.decode('utf-8', errors='ignore')
            if 'ss://' in decoded_text or 'vmess://' in decoded_text:
                return decoded_text
        except Exception:
            return text
        return text

    def _try_decode_full_blob(self, text: str) -> str:
        compact = ''.join(text.split())
        if not compact:
            return text
        try:
            decoded = base64.b64decode(self._pad(compact))
            return decoded.decode('utf-8', errors='ignore')
        except Exception:
            return text

    def _parse_lines(self, text: str) -> List[str]:
        forward_lines: List[str] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('ss://'):
                forward_lines.append(f"forward={self._normalize_ss(line)}")
            elif line.startswith('vmess://'):
                forward_lines.append(f"forward={self._normalize_vmess(line)}")
        return forward_lines

    def _normalize_ss(self, uri: str) -> str:
        try:
            rest = uri[len('ss://'):]
            if '@' in rest:
                userinfo, tail = rest.split('@', 1)
                if re.fullmatch(r'[A-Za-z0-9+/=_-]+', userinfo) and ':' not in userinfo:
                    try:
                        decoded = base64.b64decode(self._pad(userinfo)).decode('utf-8', errors='ignore')
                        if ':' in decoded and '@' not in decoded:
                            return f"ss://{decoded}@{tail}"
                    except Exception:
                        return uri
                return uri
            base_part = rest.split('#', 1)[0]
            suffix = rest[len(base_part):]
            if re.fullmatch(r'[A-Za-z0-9+/=_-]+', base_part):
                try:
                    decoded = base64.b64decode(self._pad(base_part)).decode('utf-8', errors='ignore')
                    if ':' in decoded and '@' in decoded:
                        return f"ss://{decoded}{suffix}"
                except Exception:
                    return uri
        except Exception:
            return uri
        return uri

    def _normalize_vmess(self, uri: str) -> str:
        if '@' in uri:
            return uri
        payload = uri[len('vmess://'):]
        try:
            decoded = base64.b64decode(self._pad(payload)).decode('utf-8', errors='ignore')
            data = yaml.safe_load(decoded) or {}
            server = data.get('add')
            port = data.get('port')
            uuid = data.get('id')
            alter_id = data.get('aid', '0') or '0'
            if server and port and uuid:
                return f"vmess://none:{uuid}@{server}:{port}?alterID={alter_id}"
        except Exception:
            return uri
        return uri

    def _pad(self, value: str) -> str:
        padding = (-len(value)) % 4
        return value + ('=' * padding)


class ClashYamlParser(ParserStrategy):
    name = "clash-yaml"
    def supports(self, content: FetchedContent) -> bool:
        content_type = (content.content_type or '').lower()
        if 'yaml' in content_type or 'yml' in content_type:
            return True
        head = content.text.strip().splitlines()[0] if content.text.strip() else ''
        return head.startswith('proxies:')

    def parse(self, content: FetchedContent) -> List[ForwardNode]:
        data = yaml.safe_load(content.text) or {}
        proxies = data.get('proxies', [])
        raw = parse_clash_proxies(proxies)
        return [ForwardNode(raw=line) for line in raw.splitlines() if line.strip()]
