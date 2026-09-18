#!/usr/bin/env python3
"""回归测试：前置依赖的检测、可读报错，与探活的预热重试。

三处历史缺陷，都是使用者实际撞到的：

  ① 缺 ripgrep 时抛裸 traceback。`collect-context --scope module` 直接调 `rg`，
     报的是 `FileNotFoundError: [WinError 2] 系统找不到指定的文件`——没有一句话
     说「需要装 ripgrep」。更隐蔽的是：Claude Code 环境下 `rg` 常是 **shell 函数**
     而非二进制（`which rg` 找不到 / `type -a rg` 显示 function），而 subprocess
     不走 shell 函数，「我以为装了 rg」完全不可靠。

  ② maven 被标成「可选」，但 `services.json` 的启动命令就是 `mvn spring-boot:run`。
     被标可选的 maven 缺失会直接让后端服务起不来，doctor 却放行。

  ③ 服务探活只探一次。Next.js dev server 首次请求要现场编译，单次探测超时 → FAIL，
     而同一个 URL 直接 curl 返回 200。--strict 因此被阻断，得手动再跑一次才过。
"""

from __future__ import annotations

import json

import pytest


def _repo_with_services(tmp_path, services):
    cfg = tmp_path / ".qa-agent" / "config" / "services.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({"services": services}, ensure_ascii=False), encoding="utf-8")
    return tmp_path


# --- ① 缺可执行文件要给可读报错 ---


def test_run_cmd_missing_executable_is_readable(qa, tmp_path):
    """找不到可执行文件时返回结构化失败，不抛裸 traceback。"""
    result = qa.run_cmd(["definitely-not-a-real-binary-xyz"], tmp_path, timeout=5)

    assert result["exitCode"] == 127
    assert "command not found" in result["stderr"]


def test_search_module_matches_requires_ripgrep(qa, tmp_path, monkeypatch):
    monkeypatch.setattr(qa.shutil, "which", lambda name: None)

    with pytest.raises(qa.QaAgentError) as exc:
        qa.search_module_matches(tmp_path, "order")

    message = str(exc.value)
    assert "ripgrep" in message
    assert "shell 函数" in message, "要点明 Claude Code 里的 rg 可能是 shell 函数"


# --- ② 必需性从启动命令推导 ---


def test_maven_required_when_service_uses_mvn(qa, tmp_path):
    repo = _repo_with_services(tmp_path, [{"id": "api", "startCmd": "mvn spring-boot:run"}])

    assert "maven" in qa.service_runtime_requirements(repo)


def test_maven_required_when_service_uses_wrapper(qa, tmp_path):
    repo = _repo_with_services(tmp_path, [{"id": "api", "startCmd": "./mvnw spring-boot:run"}])

    assert "maven" in qa.service_runtime_requirements(repo)


def test_node_required_when_service_uses_npm(qa, tmp_path):
    repo = _repo_with_services(tmp_path, [{"id": "web", "startCmd": "npm run dev"}])

    assert "node" in qa.service_runtime_requirements(repo)


def test_no_services_imposes_nothing(qa, tmp_path):
    assert qa.service_runtime_requirements(tmp_path) == set()


def test_gradle_service_does_not_demand_maven(qa, tmp_path):
    """推导必须来自实际命令，不是「有 java 项目就要 maven」这种猜测。"""
    repo = _repo_with_services(tmp_path, [{"id": "api", "startCmd": "./gradlew bootRun"}])

    assert qa.service_runtime_requirements(repo) == set()


# --- ③ 探活重试 ---


def _noop_sleep(monkeypatch, qa):
    monkeypatch.setattr(qa.time, "sleep", lambda _seconds: None)


def test_probe_retries_until_success(qa, monkeypatch):
    """首次超时（服务正在编译）后重试成功——本次修复的核心场景。"""
    calls = {"n": 0}

    def fake_probe(url, timeout=5):
        calls["n"] += 1
        ok = calls["n"] >= 3
        return {"url": url, "ok": ok, "status": 200 if ok else None, "detail": "probe"}

    monkeypatch.setattr(qa, "probe_http_url", fake_probe)
    _noop_sleep(monkeypatch, qa)

    result = qa.probe_http_url_with_retry("http://127.0.0.1:3000", timeout=5, attempts=3)

    assert result["ok"] is True
    assert result["attempts"] == 3


def test_probe_does_not_retry_when_first_attempt_succeeds(qa, monkeypatch):
    calls = {"n": 0}

    def fake_probe(url, timeout=5):
        calls["n"] += 1
        return {"url": url, "ok": True, "status": 200, "detail": "reachable"}

    monkeypatch.setattr(qa, "probe_http_url", fake_probe)
    _noop_sleep(monkeypatch, qa)

    result = qa.probe_http_url_with_retry("http://127.0.0.1:3000", attempts=3)

    assert result["attempts"] == 1
    assert calls["n"] == 1, "成功了不该继续重试"


def test_probe_reports_attempt_count_on_failure(qa, monkeypatch):
    monkeypatch.setattr(
        qa, "probe_http_url",
        lambda url, timeout=5: {"url": url, "ok": False, "status": None, "detail": "timed out"},
    )
    _noop_sleep(monkeypatch, qa)

    result = qa.probe_http_url_with_retry("http://127.0.0.1:3000", attempts=3)

    assert result["ok"] is False
    assert result["attempts"] == 3
    assert "重试 3 次" in result["detail"], "要让使用者知道已经试过多次，不是探了一次就判死"
