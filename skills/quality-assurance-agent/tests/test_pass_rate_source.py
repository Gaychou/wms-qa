"""测试通过率真相源：finalOutcome（执行结果）优先于 status（生命周期状态）。"""
from __future__ import annotations


def test_final_outcome_wins_over_status(qa):
    """finalOutcome=PASS 但 status=failed（生命周期残留）→ 应判通过（执行真相是 PASS）。"""
    case = {"id": "TC-P0-001", "status": "failed"}
    run = {"cases": [{"caseId": "TC-P0-001", "finalOutcome": "PASS"}]}
    assert qa._case_execution_passed(case, run) is True


def test_final_outcome_fail_wins_over_status_passed(qa):
    """finalOutcome=FAIL 但 status=passed → 应判失败（执行真相是 FAIL）。"""
    case = {"id": "TC-P0-001", "status": "passed"}
    run = {"cases": [{"caseId": "TC-P0-001", "finalOutcome": "FAIL"}]}
    assert qa._case_execution_passed(case, run) is False


def test_status_fallback_when_no_run(qa):
    """latest-run 无记录时，回退 status 里的执行结果。"""
    assert qa._case_execution_passed({"id": "TC-P0-001", "status": "passed"}, {"cases": []}) is True
    assert qa._case_execution_passed({"id": "TC-P0-001", "status": "failed"}, {"cases": []}) is False


def test_result_outcome_fallback(qa):
    """latest-run 无记录且 status=confirmed 时，回退 result.outcome。"""
    case = {"id": "TC-P0-001", "status": "confirmed", "result": {"outcome": "passed"}}
    assert qa._case_execution_passed(case, {"cases": []}) is True


def test_all_21_pass_from_run(qa):
    """21 个 finalOutcome=PASS 但 status 恒 confirmed → 通过率 100%。"""
    cases = [{"id": f"TC-{i:03d}", "status": "confirmed"} for i in range(21)]
    run = {"cases": [{"caseId": f"TC-{i:03d}", "finalOutcome": "PASS"} for i in range(21)]}
    passed = sum(1 for c in cases if qa._case_execution_passed(c, run))
    assert passed == 21, f"应 21 通过，实际 {passed}"
