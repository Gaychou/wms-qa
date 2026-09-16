"""测试风险覆盖投影：traceability 反推 coveredByCases。"""
from __future__ import annotations

import pytest


def test_project_risk_coverage_maps_traceability_to_risks(qa):
    cases = {
        "cases": [
            {"id": "TC-P0-001", "traceability": ["RISK-P0-001", "RISK-P1-004"]},
            {"id": "TC-P1-008", "traceability": ["RISK-P1-004"]},
            {"id": "TC-P2-014", "traceability": ["RISK-P1-005"]},
            {"id": "TC-P0-002", "traceability": []},
        ]
    }

    coverage = qa.project_risk_coverage(cases)

    assert coverage["RISK-P0-001"] == ["TC-P0-001"]
    assert coverage["RISK-P1-004"] == ["TC-P0-001", "TC-P1-008"]
    assert coverage["RISK-P1-005"] == ["TC-P2-014"]
    assert "TC-P0-002" not in coverage  # 无 traceability 不产生键


def test_project_risk_coverage_dedups(qa):
    cases = {
        "cases": [
            {"id": "TC-P0-001", "traceability": ["RISK-P0-001", "RISK-P0-001"]},
        ]
    }

    coverage = qa.project_risk_coverage(cases)

    assert coverage["RISK-P0-001"] == ["TC-P0-001"]


def test_project_risk_coverage_empty_cases(qa):
    assert qa.project_risk_coverage({"cases": []}) == {}
    assert qa.project_risk_coverage({}) == {}
