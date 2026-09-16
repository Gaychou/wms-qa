"""测试审查硬门禁：verdict 参与判定 + finding 可追溯。"""
from __future__ import annotations


def _finding(severity="P1", verdict="CONFIRMED", file="src/X.java", evidence="读代码确认"):
    return {"id": "CR-001", "severity": severity, "verdict": verdict, "file": file,
            "summary": "问题", "evidence": evidence}


def test_plausible_p0_p1_is_blocking(qa):
    """PLAUSIBLE（待确认）的 P1 未排除 = 风险未清，必须 blocking。"""
    review = {"status": "passed", "findings": [_finding(verdict="PLAUSIBLE")]}
    result = qa.assert_code_review_data(review)
    assert result["status"] == "failed", "PLAUSIBLE 的 P1 必须 blocking"


def test_rejected_finding_not_blocking(qa):
    """REJECTED（已排除）的 finding 不 blocking。"""
    review = {"status": "passed", "findings": [_finding(verdict="REJECTED")]}
    result = qa.assert_code_review_data(review)
    assert result["status"] == "passed"


def test_finding_missing_file_fails(qa):
    review = {"status": "passed", "findings": [_finding(file=None)]}
    result = qa.assert_code_review_data(review)
    types = [f["type"] for f in result["findings"]]
    assert "finding-missing-file" in types


def test_finding_missing_evidence_fails(qa):
    review = {"status": "passed", "findings": [_finding(evidence=None)]}
    result = qa.assert_code_review_data(review)
    types = [f["type"] for f in result["findings"]]
    assert "finding-missing-evidence" in types


def test_p2_finding_without_file_not_required(qa):
    """P2 不 blocking，可追溯性要求只针对 P0/P1 blocking finding。"""
    review = {"status": "passed", "findings": [_finding(severity="P2", file=None, evidence=None)]}
    result = qa.assert_code_review_data(review)
    assert result["status"] == "passed"
