"""测试 call_model 的 stream 和 max_tokens 修复"""
import json
import pytest
from unittest.mock import Mock, patch
from qa_agent import call_model


def test_call_model_non_stream_model_uses_stream_false():
    """验证非流式模型（不在 STREAM_REQUIRED_MODELS）显式发送 stream: false"""
    with patch('urllib.request.urlopen') as mock_urlopen:
        # 模拟成功响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": '{"review": "ok"}'}}]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        with patch('urllib.request.Request') as mock_request:
            call_model(
                model="test-model",
                prompt="test prompt",
                base_url="http://test.com",
                api_key="test-key",
                timeout=30
            )

            # 检查 Request 的 data 参数
            call_args = mock_request.call_args
            request_body = json.loads(call_args[1]['data'].decode())

            assert 'stream' in request_body, "Request body must include 'stream' field"
            assert request_body['stream'] is False, "stream must be explicitly False"


def test_call_model_max_tokens_sufficient():
    """验证 max_tokens 足够大（建议 16000+）"""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": '{"review": "ok"}'}}]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        with patch('urllib.request.Request') as mock_request:
            call_model(
                model="test-model",
                prompt="test prompt",
                base_url="http://test.com",
                api_key="test-key",
                timeout=30
            )

            call_args = mock_request.call_args
            request_body = json.loads(call_args[1]['data'].decode())

            assert request_body['max_tokens'] >= 16000, "max_tokens should be at least 16000 for 18-case reviews"


def test_call_model_handles_length_truncation():
    """验证能识别 finish_reason=length 的截断响应"""
    with patch('urllib.request.urlopen') as mock_urlopen:
        # 模拟 DeepSeek 的截断响应：content=null, finish_reason=length
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {"content": None},
                "finish_reason": "length"
            }],
            "usage": {"completion_tokens": 11999}
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = call_model(
            model="deepseek-v4-pro",
            prompt="test prompt",
            base_url="http://test.com",
            api_key="test-key",
            timeout=30
        )

        assert not result["ok"]
        assert "截断" in result["error"] or "length" in result["error"].lower()


def test_call_model_stream_true_for_gpt_5_4():
    """验证 gpt-5.4 发送 stream: true，且聚合 SSE 时只取 delta.content（忽略 reasoning_content）"""
    chunks = [
        {"choices": [{"index": 0, "delta": {"reasoning_content": "internal thought", "role": "assistant"}, "finish_reason": None}]},
        {"choices": [{"index": 0, "delta": {"content": '{"ok": true}'}, "finish_reason": "stop"}]},
    ]
    sse_raw = "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = sse_raw.encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        with patch('urllib.request.Request') as mock_request:
            result = call_model(
                model="gpt-5.4",
                prompt="test prompt",
                base_url="http://test.com",
                api_key="test-key",
                timeout=30
            )

            request_body = json.loads(mock_request.call_args[1]['data'].decode())
            assert request_body['stream'] is True, "gpt-5.4 must send stream: true"

            assert result["ok"] is True, result
            assert result["review"]["ok"] is True
