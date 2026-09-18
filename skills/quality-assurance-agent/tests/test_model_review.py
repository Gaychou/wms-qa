"""测试 review_cases 的整体超时与失败隔离（评审失败不中断后续流程）"""
import os
from types import SimpleNamespace
from unittest.mock import patch

from qa_agent import review_cases


def _args(**overrides):
    base = dict(
        cases="cases.json",
        context=None,
        models="gpt-5.4,claude-sonnet-5,deepseek-v4-pro",
        dry_run=False,
        api_key_env="QA_AGENT_LLM_API_KEY",
        base_url_env="QA_AGENT_LLM_BASE_URL",
        base_url="https://api.example.com/v1",
        timeout=180,
        max_retries=2,
        retry_backoff_seconds=2.0,
        output=".qa-agent/current/model-review.json",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_review_cases_missing_key_does_not_raise():
    """缺 API key 时不再抛异常，而是写出「全部模型失败」结果"""
    args = _args()
    with patch.dict(os.environ, {}, clear=True), \
            patch("qa_agent.read_json", return_value={"cases": []}), \
            patch("qa_agent.write_json") as mock_write:
        review_cases(args)  # 不应抛出 QaAgentError

        data = mock_write.call_args[0][1]
        assert data["modelsSucceeded"] == []
        assert len(data["modelsFailed"]) == 3
        assert all(r["ok"] is False for r in data["rawResults"])


def test_all_models_failed_marks_status_skipped():
    """全部模型失败时必须标 skipped。

    否则 findings: [] 有两种读法——「审过了，没问题」和「根本没审」——产物长得一样。
    使用者实测时三个模型全失败、产物照常写出，差点按「已审查且干净」理解。
    """
    args = _args()
    with patch.dict(os.environ, {}, clear=True), \
            patch("qa_agent.read_json", return_value={"cases": []}), \
            patch("qa_agent.write_json") as mock_write:
        review_cases(args)

        data = mock_write.call_args[0][1]
        assert data["status"] == "skipped", "未执行审查不能看起来像审查通过"
        assert "不代表审查通过" in data["note"]


def test_successful_review_marks_status_reviewed():
    args = _args(models="one-model")
    with patch.dict(os.environ, {"QA_AGENT_LLM_API_KEY": "k"}, clear=True), \
            patch("qa_agent.read_json", return_value={"cases": []}), \
            patch("qa_agent.write_json") as mock_write, \
            patch("qa_agent.call_model", return_value={"model": "m", "ok": True, "review": {}}):
        review_cases(args)

        data = mock_write.call_args[0][1]
        assert data["status"] == "reviewed"
        assert "note" not in data


def test_review_cases_model_exception_isolated():
    """单个模型抛异常不中断评审，记录为失败继续产出结果"""
    args = _args()

    def boom(*a, **k):
        raise RuntimeError("boom")

    with patch.dict(os.environ, {"QA_AGENT_LLM_API_KEY": "k"}, clear=True), \
            patch("qa_agent.read_json", return_value={"cases": []}), \
            patch("qa_agent.write_json") as mock_write, \
            patch("qa_agent.call_model", side_effect=boom):
        review_cases(args)  # 不应抛出异常

        data = mock_write.call_args[0][1]
        assert len(data["modelsFailed"]) == 3
        assert all("评审异常" in r["error"] for r in data["modelsFailed"])


def test_review_cases_overall_timeout_marks_pending():
    """整体超时后，未完成模型标记为失败；整体超时 = 单模型超时 + 30s"""
    args = _args(timeout=180)

    def fake_wait(fs, timeout):
        assert timeout == 210, "整体超时应为单模型超时 + 30s"
        return set(), set(fs)  # 模拟：所有 future 均未在整体超时内完成

    with patch.dict(os.environ, {"QA_AGENT_LLM_API_KEY": "k"}, clear=True), \
            patch("qa_agent.read_json", return_value={"cases": []}), \
            patch("qa_agent.write_json") as mock_write, \
            patch("qa_agent.call_model", return_value={"model": "m", "ok": True, "review": {}}), \
            patch("qa_agent.concurrent.futures.wait", side_effect=fake_wait):
        review_cases(args)

        data = mock_write.call_args[0][1]
        assert len(data["modelsFailed"]) == 3
        assert all("整体超时" in r["error"] for r in data["modelsFailed"])
