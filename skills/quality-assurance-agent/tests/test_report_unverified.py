"""测试报告 blocked 用例独立呈现。"""
from __future__ import annotations


def _cases():
    return [
        {"id": "TC-P0-001", "title": "正常用例", "status": "passed"},
        {"id": "TC-P0-002", "title": "阻塞用例", "status": "blocked"},
        {"id": "TC-P0-003", "title": "失败用例", "status": "failed"},
    ]


def test_unverified_section_lists_blocked_cases(qa):
    spec_tasks = {"tasks": [{"sourceCaseId": "TC-P0-002", "executionStatus": "blocked", "blocker": "缺数据"}]}
    html = qa._render_unverified_cases(_cases(), spec_tasks)
    assert "未验证" in html
    assert "TC-P0-002" in html
    assert "TC-P0-001" not in html  # passed 用例不在未验证列表
    assert "TC-P0-003" not in html  # failed 用例是"已执行失败"，不是"未验证"


def test_unverified_section_empty_when_no_blocked(qa):
    cases = [{"id": "TC-P0-001", "title": "正常", "status": "passed"}]
    assert qa._render_unverified_cases(cases, {"tasks": []}) == ""
