from __future__ import annotations

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import requests

from features.proxy_pool.application.ports import ForwardTester
from features.proxy_pool.domain.subscriptions import ForwardNode, GliderConfig


@dataclass
class GliderForwardTester(ForwardTester):
    glider_path: Path
    listen_host: str = '127.0.0.1'
    start_port: int = 18081
    timeout: int = 8
    max_workers: int = 20
    test_url: str = 'http://www.msftconnecttest.com/connecttest.txt#expect=200'
    expect_statuses: Iterable[int] = (200, 204)
    config_dir: Path = Path('glider')

    def filter_usable(self, nodes: List[ForwardNode]) -> List[ForwardNode]:
        if not nodes:
            return []
        self._ensure_glider_executable()
        usable: List[ForwardNode] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {
                executor.submit(self._test_node, index, node): node
                for index, node in enumerate(nodes)
            }
            for future in as_completed(future_map):
                node = future_map[future]
                try:
                    if future.result():
                        usable.append(node)
                except Exception:
                    continue
        if not usable:
            return []
        return usable

    def _ensure_glider_executable(self):
        if not self.glider_path.exists():
            raise FileNotFoundError(f"glider executable not found at {self.glider_path}")
        try:
            self.glider_path.chmod(0o755)
        except Exception:
            pass

    def _test_node(self, index: int, node: ForwardNode) -> bool:
        port = self.start_port + index
        config_path = self.config_dir / f'glider.test.{port}.conf'
        config_content = self._config_template(port) + node.as_line()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config_content, encoding='utf-8')
        proc = None
        try:
            proc = subprocess.Popen([str(self.glider_path), '-config', str(config_path)])
            time.sleep(0.8)
            proxies: Dict[str, str] = {
                'http': f'http://{self.listen_host}:{port}',
                'https': f'http://{self.listen_host}:{port}',
            }
            response = requests.get(self.test_url, proxies=proxies, timeout=self.timeout)
            return response.status_code in set(self.expect_statuses)
        except Exception:
            return False
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
            try:
                config_path.unlink()
            except FileNotFoundError:
                pass
            except Exception:
                pass

    def _config_template(self, port: int) -> str:
        return (
            "# verbose\nverbose=true\n\n"
            f"listen={self.listen_host}:{port}\n\n"
            "strategy=rr\n\n"
            "check=http://www.msftconnecttest.com/connecttest.txt#expect=200\n\n"
            "checkinterval=300\n\n"
        )
