"""测试通过率真相源：status 优先，latest-run 失败不拖成 0%。"""
from __future__ import annotations

import pytest


def test_status_passed_wins_over_empty_run(qa):
    """status=passed 应直接判通过，即使 latest-run 为空（聚合失败）。"""
    assert qa._case_execution_passed({"id": "TC-P0-001", "status": "passed"}, {}) is True


def test_status_failed_is_not_passed(qa):
    assert qa._case_execution_passed({"id": "TC-P0-001", "status": "failed"}, {}) is False


def test_status_blocked_is_not_passed(qa):
    assert qa._case_execution_passed({"id": "TC-P0-001", "status": "blocked"}, {}) is False


def test_result_outcome_fallback(qa):
    case = {"id": "TC-P0-001", "status": "confirmed", "result": {"outcome": "passed"}}
    assert qa._case_execution_passed(case, {}) is True


def test_run_final_outcome_last_resort(qa):
    case = {"id": "TC-P0-001", "status": "confirmed"}
    run = {"cases": [{"caseId": "TC-P0-001", "finalOutcome": "PASS"}]}
    assert qa._case_execution_passed(case, run) is True


def test_pass_rate_not_zero_with_status(qa):
    """16 passed / 1 failed / 1 blocked → 通过率 88%（不是 0%）。"""
    cases = [
        {"id": f"TC-{i:03d}", "status": "passed"} for i in range(16)
    ] + [
        {"id": "TC-FAIL", "status": "failed"},
        {"id": "TC-BLOCK", "status": "blocked"},
    ]
    # 空 run_data（模拟 latest-run 聚合失败）
    passed = sum(1 for c in cases if qa._case_execution_passed(c, {}))
    assert passed == 16, f"应 16 通过，实际 {passed}"
    rate = int(passed * 100 / len(cases))
    assert rate == 88, f"通过率应 88%，实际 {rate}%"
