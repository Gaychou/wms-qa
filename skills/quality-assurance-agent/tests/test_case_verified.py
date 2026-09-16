"""测试「用例层 verified 闸门」：blocked 用例不能通过 completion。"""
from __future__ import annotations


def _cases():
    return {
        "version": "1.0",
        "cases": [
            {"id": "TC-P0-001", "priority": "P0", "title": "用例", "module": "order",
             "type": "business", "layer": "api", "automation": "automated", "status": "confirmed"},
        ],
    }


def _task(case_id="TC-P0-001", layer="api", exec_status="passed", evidence=None):
    return {
        "id": f"SPEC-{case_id}-API-001",
        "sourceCaseId": case_id,
        "priority": "P0",
        "layer": layer,
        "targetFile": f"tests/api/{case_id.lower()}.sh",
        "testName": f"{case_id} 测试",
        "command": "bash test.sh",
        "assertions": ["code=200"],
        "implementationStatus": "implemented",
        "executionStatus": exec_status,
        "evidence": evidence if evidence is not None else ["PASS [code]: 200"],
    }


def test_case_verified_when_has_passed_task(qa):
    spec_tasks = {"tasks": [_task()]}
    result = qa.assert_completion_data(_cases(), spec_tasks)
    types = [f["type"] for f in result["findings"]]
    assert "case-not-verified" not in types, f"有 passed task 不应报未验证：{types}"


def test_case_not_verified_when_all_blocked(qa):
    """用例所有 task 都 blocked → 用例未验证，门禁 fail（核心闸门）。"""
    spec_tasks = {"tasks": [_task(exec_status="blocked", evidence=[])]}
    result = qa.assert_completion_data(_cases(), spec_tasks, allow_blocked=True)
    types = [f["type"] for f in result["findings"]]
    assert "case-not-verified" in types, f"全 blocked 用例必须判未验证：{types}"
    # 即使 allow_blocked，用例未验证也必须 fail，不能 complete_with_allowed_gaps
    assert result["status"] == "failed"
    assert result["decision"] != "complete_with_allowed_gaps"


def test_case_verified_with_mixed_passed_and_blocked(qa):
    """用例有 passed + blocked 混合 → 有 passed 就算 verified。"""
    spec_tasks = {"tasks": [
        _task(layer="api", exec_status="passed"),
        _task(layer="unit", exec_status="blocked", evidence=[]),
    ]}
    result = qa.assert_completion_data(_cases(), spec_tasks, allow_blocked=True)
    types = [f["type"] for f in result["findings"]]
    assert "case-not-verified" not in types


def test_case_not_verified_when_only_unimplemented(qa):
    """用例 task 都是 not-implemented（映射没实现）→ 未验证。"""
    spec_tasks = {"tasks": [_task(exec_status="not-run", evidence=[])]}
    result = qa.assert_completion_data(_cases(), spec_tasks)
    types = [f["type"] for f in result["findings"]]
    assert "case-not-verified" in types
