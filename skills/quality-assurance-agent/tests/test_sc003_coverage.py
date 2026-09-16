"""测试 SC-003 覆盖交叉校验能发现「全缺口」失真。"""
from __future__ import annotations

import pytest


def _risks(n=3):
    return {"risks": [{"id": f"RISK-P0-{i:03d}", "priority": "P0", "risk": f"风险{i}"} for i in range(1, n + 1)]}


def _report_html(covered_badges=0):
    badges = ''.join('<span class="b passed">已覆盖</span>' for _ in range(covered_badges))
    return f"<html>{badges}</html>"


def test_sc003_detects_all_missing_when_traceability_covers(qa):
    """用例 traceability 覆盖 3 条风险，但报告展示 0 个已覆盖 → 必须报警（旧逻辑会漏）。"""
    coverage_map = {"RISK-P0-001": ["TC-P0-001"], "RISK-P0-002": ["TC-P0-002"], "RISK-P0-003": ["TC-P0-003"]}
    result = qa._check_sc003_coverage(_report_html(0), _risks(3), coverage_map)

    assert result is not None, "覆盖失真必须被发现"
    assert result["id"] == "SC-003"
    assert result["severity"] == "high"


def test_sc003_passes_when_badges_match_projection(qa):
    coverage_map = {"RISK-P0-001": ["TC-P0-001"], "RISK-P0-002": ["TC-P0-002"]}
    result = qa._check_sc003_coverage(_report_html(2), _risks(2), coverage_map)

    assert result is None


def test_sc003_detects_risk_covered_but_not_rendered(qa):
    """风险被用例覆盖（投影非空），但报告少渲染了 badge。"""
    coverage_map = {"RISK-P0-001": ["TC-P0-001"], "RISK-P0-002": ["TC-P0-002"], "RISK-P0-003": ["TC-P0-003"]}
    result = qa._check_sc003_coverage(_report_html(1), _risks(3), coverage_map)

    assert result is not None
