#!/usr/bin/env python3
"""测试 call_model 的 stream 行为与 max_tokens。

契约（2026-09 变更）：
- **默认流式**。流式是超集（SSE 聚合本已实现），且多数网关默认或只支持流式。
  旧实现靠一个硬编码的模型集合（STREAM_REQUIRED_MODELS = {"gpt-5.4"}）去猜谁
  需要流式——换个同样强制流式的网关就撞 400，用户还没法自己打开。
- 端点确实不支持流式时，**自动降级重试一次非流式**，用户不必预先知道配什么。
- 降级只在错误体同时提到 stream 和否定词时触发，无关的 400 不该被误判。
"""

import io
import json
import urllib.error
from unittest.mock import Mock, patch

from qa_agent import call_model


def _ok_response(payload: dict) -> Mock:
    resp = Mock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__ = Mock(return_value=resp)
    resp.__exit__ = Mock(return_value=False)
    return resp


def _http_error(code: int, body: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="http://test.com/v1/chat/completions",
        code=code,
        msg="err",
        hdrs=None,
        fp=io.BytesIO(body.encode()),
    )


def _request_bodies(mock_request) -> list[dict]:
    return [json.loads(c[1]["data"].decode()) for c in mock_request.call_args_list]


# ── 默认流式 ──────────────────────────────────────────────────────────────

def test_streams_by_default_for_any_model():
    """任意模型名都默认发 stream: true，不再按模型名猜。"""
    sse = 'data: {"choices":[{"delta":{"content":"{\\"ok\\":true}"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'

    with patch("urllib.request.urlopen") as mock_urlopen, patch("urllib.request.Request") as mock_request:
        resp = Mock()
        resp.read.return_value = sse.encode()
        resp.__enter__ = Mock(return_value=resp)
        resp.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = resp

        result = call_model(model="some-arbitrary-model", prompt="p",
                            base_url="http://test.com", api_key="k", timeout=30)

        assert _request_bodies(mock_request)[0]["stream"] is True, "默认应走流式"
        assert result["ok"] is True, result


def test_can_turn_stream_off():
    with patch("urllib.request.urlopen") as mock_urlopen, patch("urllib.request.Request") as mock_request:
        mock_urlopen.return_value = _ok_response({"choices": [{"message": {"content": '{"ok": true}'}}]})

        call_model(model="m", prompt="p", base_url="http://test.com", api_key="k",
                   timeout=30, stream=False)

        assert _request_bodies(mock_request)[0]["stream"] is False


# ── 自动降级 ──────────────────────────────────────────────────────────────

def test_downgrades_when_endpoint_rejects_stream():
    """端点回「stream 不支持」时，自动改用非流式重试一次并成功。"""
    with patch("urllib.request.urlopen") as mock_urlopen, patch("urllib.request.Request") as mock_request:
        mock_urlopen.side_effect = [
            _http_error(400, '{"error":"stream is not supported by this endpoint"}'),
            _ok_response({"choices": [{"message": {"content": '{"ok": true}'}}]}),
        ]

        result = call_model(model="m", prompt="p", base_url="http://test.com",
                            api_key="k", timeout=30)

        bodies = _request_bodies(mock_request)
        assert len(bodies) == 2, f"应发出两次请求（流式失败 → 非流式），实际 {len(bodies)}"
        assert bodies[0]["stream"] is True
        assert bodies[1]["stream"] is False, "降级后必须改用非流式"
        assert result["ok"] is True, result


def test_unrelated_400_does_not_downgrade():
    """无关的 400（错误体没提 stream）不该被误判成「不支持流式」。"""
    with patch("urllib.request.urlopen") as mock_urlopen, patch("urllib.request.Request") as mock_request:
        mock_urlopen.side_effect = _http_error(400, '{"error":"model not found"}')

        result = call_model(model="m", prompt="p", base_url="http://test.com",
                            api_key="k", timeout=30, max_retries=0)

        bodies = _request_bodies(mock_request)
        assert len(bodies) == 1, "不该重试"
        assert bodies[0]["stream"] is True
        assert result["ok"] is False


# ── 响应解析 ──────────────────────────────────────────────────────────────

def test_sse_aggregates_delta_content_only():
    """SSE 聚合只取 delta.content，忽略 reasoning_content 之类的旁路字段。"""
    chunks = [
        {"choices": [{"index": 0, "delta": {"reasoning_content": "internal thought", "role": "assistant"}, "finish_reason": None}]},
        {"choices": [{"index": 0, "delta": {"content": '{"ok": true}'}, "finish_reason": "stop"}]},
    ]
    sse_raw = "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"

    with patch("urllib.request.urlopen") as mock_urlopen:
        resp = Mock()
        resp.read.return_value = sse_raw.encode()
        resp.__enter__ = Mock(return_value=resp)
        resp.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = resp

        result = call_model(model="m", prompt="p", base_url="http://test.com", api_key="k", timeout=30)

        assert result["ok"] is True, result
        assert result["review"]["ok"] is True


def test_max_tokens_sufficient():
    with patch("urllib.request.urlopen") as mock_urlopen, patch("urllib.request.Request") as mock_request:
        mock_urlopen.return_value = _ok_response({"choices": [{"message": {"content": '{"ok": true}'}}]})

        call_model(model="m", prompt="p", base_url="http://test.com", api_key="k", timeout=30)

        assert _request_bodies(mock_request)[0]["max_tokens"] >= 16000


def test_handles_length_truncation():
    """finish_reason=length 的截断响应要被识别出来，而不是当成空内容。"""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _ok_response({
            "choices": [{"message": {"content": None}, "finish_reason": "length"}],
            "usage": {"completion_tokens": 11999},
        })

        result = call_model(model="m", prompt="p", base_url="http://test.com",
                            api_key="k", timeout=30, stream=False)

        assert not result["ok"]
        assert "截断" in result["error"] or "length" in result["error"].lower()
