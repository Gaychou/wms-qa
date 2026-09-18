#!/usr/bin/env python3
"""回归测试：风险覆盖投影只能采信「真正的风险关联」。

历史缺陷（会向人输出与事实相反的结论）：

  `test-cases.json` 的 `traceability` 按 schema 是**混合内容**——requirement id、
  issue id、代码路径、API 路径（见 references/test-case-schema.md）。而
  `project_risk_coverage()` 曾把它当作「关联的 risk ID 列表」，逐项当风险号。

  于是使用者完全照 schema 写（traceability 里放 API 路径）时，投影结果为空，
  报告显示「识别 7 条，已覆盖 0 条，缺口 7 条」——而每条风险其实都有已执行通过的
  用例在管。报告输出的是与事实完全相反的结论，且长得像真实缺口，使用者会据此
  去补并不存在的覆盖。

  更麻烦的是当时拦不住：SC-003 的两边（covered_expected 与渲染出的 badge 数）
  都来自同一个 coverage_map，投影错则两边一起错、数值恒等，必然通过。

修复：投影只采信显式 `riskIds`（新字段）+ 形态正确的 `traceability` 条目；
另加 SC-007，用**独立于投影的文本扫描**做交叉比对，专抓投影漏读。
"""

from __future__ import annotations


def _cases(*cases):
    return {"cases": list(cases)}


# ── 投影：只认真正的风险关联 ──────────────────────────────────────────────


def test_explicit_risk_ids_are_projected(qa):
    """显式 riskIds 是主源。"""
    coverage = qa.project_risk_coverage(
        _cases({"id": "TC-P0-001", "riskIds": ["RISK-P0-001", "RISK-P1-002"]})
    )

    assert coverage == {"RISK-P0-001": ["TC-P0-001"], "RISK-P1-002": ["TC-P0-001"]}


def test_api_path_in_traceability_is_not_a_risk(qa):
    """本次修复的核心：API 路径不是风险号，不得进投影（旧逻辑会把它当风险）。"""
    coverage = qa.project_risk_coverage(
        _cases({"id": "TC-P0-001", "traceability": ["POST /open-box/open-by-usd"]})
    )

    assert coverage == {}, f"API 路径被误当风险号：{coverage}"


def test_legacy_risk_id_in_traceability_still_projects(qa):
    """兼容旧数据：风险号写在 traceability 里且形态正确，仍然认。"""
    coverage = qa.project_risk_coverage(
        _cases({"id": "TC-P0-001", "traceability": ["RISK-P0-001"]})
    )

    assert coverage == {"RISK-P0-001": ["TC-P0-001"]}


def test_mixed_traceability_only_projects_risk_shaped_entries(qa):
    """混合内容里只挑出风险号，其余（需求号、代码路径）不进投影。"""
    coverage = qa.project_risk_coverage(
        _cases({"id": "TC-P0-001", "traceability": ["REQ-001", "src/Foo.java", "RISK-P0-002"]})
    )

    assert coverage == {"RISK-P0-002": ["TC-P0-001"]}


def test_explicit_and_traceability_sources_are_merged_without_duplicates(qa):
    """两个来源合并去重，保持首次出现顺序。"""
    coverage = qa.project_risk_coverage(
        _cases({"id": "TC-P0-001", "riskIds": ["RISK-P0-001"], "traceability": ["RISK-P0-001", "RISK-P0-002"]})
    )

    assert coverage == {"RISK-P0-001": ["TC-P0-001"], "RISK-P0-002": ["TC-P0-001"]}


# ── SC-007：独立扫描，专抓投影漏读 ────────────────────────────────────────


def test_sc007_catches_the_reported_failure(qa):
    """复现本次事故：traceability 写 API 路径、风险号写在 risk 字段。

    投影为空 → 报告谎报 0 覆盖。SC-007 必须报出来。
    """
    cases_data = _cases(
        {
            "id": "TC-P0-001",
            "risk": "RISK-P0-001 资金重复发放",
            "traceability": ["POST /open-box/open-by-usd"],
        }
    )
    coverage_map = qa.project_risk_coverage(cases_data)

    assert coverage_map == {}, "前提：投影在旧写法下确实是空的"

    result = qa._check_sc007_projection_completeness(cases_data, coverage_map)

    assert result is not None, "投影漏读必须被发现——否则错误结论直接送到人面前"
    assert result["id"] == "SC-007"
    assert result["severity"] == "high"
    assert "RISK-P0-001" in result["summary"]


def test_sc007_silent_when_risk_is_linked(qa):
    """正常关联时不得报警（自检 findings 会直接 exit 1，误报即阻断）。"""
    cases_data = _cases({"id": "TC-P0-001", "risk": "资金重复发放", "riskIds": ["RISK-P0-001"]})

    assert qa._check_sc007_projection_completeness(cases_data, qa.project_risk_coverage(cases_data)) is None


def test_sc007_ignores_risk_id_inside_result_evidence(qa):
    """原始证据/日志里出现风险号不构成关联声明，不得误报。"""
    cases_data = _cases(
        {
            "id": "TC-P0-001",
            "riskIds": ["RISK-P0-001"],
            "result": {"log": "assert RISK-P0-009 failed at line 42"},
        }
    )

    assert qa._check_sc007_projection_completeness(cases_data, qa.project_risk_coverage(cases_data)) is None


def test_sc007_silent_on_non_risk_traceability(qa):
    """traceability 里全是代码路径/API 路径、也确实没关联任何风险 → 不报。"""
    cases_data = _cases({"id": "TC-P0-001", "traceability": ["POST /open-box/exchange", "src/Foo.java"]})

    assert qa._check_sc007_projection_completeness(cases_data, qa.project_risk_coverage(cases_data)) is None
