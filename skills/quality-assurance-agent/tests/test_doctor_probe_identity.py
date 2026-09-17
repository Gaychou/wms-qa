#!/usr/bin/env python3
"""回归测试：探活必须能识别「端口上到底是谁」。

历史问题：probe_http_url 把 200 <= status < 500 一律判为可达，于是**任何** HTTP
响应都算「服务在」。实测场景——配置里 api 指向 127.0.0.1:8080，端口被一个无关的
Python 文件服务器（http.server）占用：

    doctor 报  service:api:reachable  ✅
    E2E 报     page.evaluate: TypeError: Failed to fetch

排查成本极高，因为 doctor 已经给了「可达」的绿灯。根因是探活只证明「有人在那监听」，
不证明「监听的是正确的服务」。

两处修复：
  1. probe_http_url 带回对端身份（Server 头 + Content-Type），被无关进程占端口时
     一眼可辨；
  2. services.json 声明的 healthUrl 现在会真正用于探活（此前 default_local_stack_targets
     没有把它传下去，doctor 只能探 baseUrl 根路径——而根路径天然 404，证明不了任何事）。
"""

import functools
import http.server
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import _server_signature, default_local_stack_targets, probe_http_url


class _StubHandler(http.server.BaseHTTPRequestHandler):
    """伪装成一个无关的常驻服务：只回 200，并带上可识别的 Server 头。"""

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler 的约定命名
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # 测试里不要往 stderr 刷访问日志
        pass


@pytest.fixture()
def stub_service():
    """在临时端口上起一个可识别身份的桩服务。"""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_probe_reports_peer_identity(stub_service):
    """探活结果必须带上对端身份——否则端口被占时无从判断。"""
    result = probe_http_url(stub_service, timeout=5)

    assert result["ok"] is True, "桩服务确实在监听，可达性判定应通过"
    identity = result.get("server") or ""
    assert identity, "未带回对端身份，端口被无关进程占用时无法排查"
    # BaseHTTPRequestHandler 默认发 Server: BaseHTTP/x.y Python/z.w
    assert "Python" in identity or "BaseHTTP" in identity, (
        f"对端身份里应能看出这是个 Python 服务，实际拿到：{identity!r}"
    )


def test_server_signature_joins_server_and_content_type():
    class _Headers(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    assert _server_signature(_Headers({"Server": "nginx/1.25"})) == "nginx/1.25"
    assert _server_signature(_Headers({"Content-Type": "application/json"})) == "application/json"
    assert _server_signature(
        _Headers({"Server": "SimpleHTTP/0.6 Python/3.11", "Content-Type": "text/html"})
    ) == "SimpleHTTP/0.6 Python/3.11 / text/html"
    assert _server_signature(None) == ""


def test_service_config_health_url_reaches_probe_targets(tmp_path):
    """services.json 声明的 healthUrl 必须传到探活目标上。

    此前 default_local_stack_targets 只带 url，doctor 于是只能探 baseUrl 根路径，
    而根路径对很多服务天然 404 —— 拿 404 当「可达」等于没检查。
    """
    repo = tmp_path / "repo"
    (repo / ".qa-agent" / "config").mkdir(parents=True)
    (repo / ".qa-agent" / "config" / "services.json").write_text(
        """{
  "version": "1.0",
  "services": [
    {
      "id": "api",
      "baseUrlEnv": "QA_API_BASE_URL",
      "required": true,
      "dir": "backend",
      "startCmd": "mvn spring-boot:run",
      "readySignal": "Started",
      "healthUrl": "http://127.0.0.1:8080/actuator/health"
    }
  ]
}""",
        encoding="utf-8",
    )
    (repo / ".qa-agent" / "config" / "env.shared").write_text(
        "QA_API_BASE_URL=http://127.0.0.1:8080\n", encoding="utf-8"
    )

    targets = default_local_stack_targets(repo)
    assert targets, "应从 services.json 解析出探活目标"

    api = next(t for t in targets if t["name"] == "api")
    assert api.get("healthUrl") == "http://127.0.0.1:8080/actuator/health", (
        "healthUrl 未传到探活目标，doctor 将退化成探 baseUrl 根路径"
    )
    assert api.get("readySignal") == "Started", "readySignal 也应保留"
