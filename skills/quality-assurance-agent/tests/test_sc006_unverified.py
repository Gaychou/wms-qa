"""测试 SC-006：未验证用例不能被「可以合并」掩盖。"""
from __future__ import annotations


def _completion(has_unverified=True):
    findings = [{"type": "case-not-verified", "severity": "fail", "sourceCaseId": "TC-P0-002"}] if has_unverified else []
    return {"findings": findings}


def test_unverified_but_ready_is_flagging(qa):
    """completion 有 case-not-verified，但报告判「可以合并」→ 必须报警。"""
    report = "<html>可以合并（就绪）</html>"
    result = qa._check_sc006_unverified_cases(report, _completion(True))
    assert result is not None, "未验证用例被「可以合并」掩盖必须报警"
    assert result["id"] == "SC-006"


def test_no_unverified_no_flag(qa):
    result = qa._check_sc006_unverified_cases("<html>可以合并（就绪）</html>", _completion(False))
    assert result is None


def test_unverified_but_not_ready_no_flag(qa):
    """completion 有 case-not-verified，但报告如实判 Not Ready → 不报警。"""
    report = "<html>暂不建议合并</html>"
    result = qa._check_sc006_unverified_cases(report, _completion(True))
    assert result is None
