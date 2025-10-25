import sys
from typing import List


def parse_config(array: list) -> str:
    # Convert Clash proxies (list of dict) to glider forward= lines
    ss = []
    vmess = []

    supported_ciphers = {
        'aes-128-gcm', 'aes-256-gcm', 'chacha20-ietf-poly1305',
        'aes-128-ctr', 'aes-192-ctr', 'aes-256-ctr',
        'aes-128-cfb', 'aes-192-cfb', 'aes-256-cfb',
        'chacha20-ietf', 'xchacha20-ietf-poly1305'
    }

    for node in array or []:
        t = node.get('type')
        if t == 'ss':
            cipher = node.get('cipher')
            if cipher not in supported_ciphers:
                continue
            node_str = f"ss://{cipher}:{node.get('password','')}@{node.get('server','')}:{node.get('port','')}#{node.get('name','')}"
            ss.append(node_str)
        elif t == 'vmess':
            node_str = f"vmess://none:{node.get('uuid','')}@{node.get('server','')}:{node.get('port','')}?alterID={node.get('alterId','0')}"
            vmess.append(node_str)

    output = ""
    for node in ss:
        output += f"forward={node}\n"
    for node in vmess:
        output += f"forward={node}\n"
    return output

