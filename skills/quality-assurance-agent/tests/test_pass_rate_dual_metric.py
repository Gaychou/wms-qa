#!/usr/bin/env python3
"""回归测试：通过率与验证覆盖必须分开呈现，且与 SC-001 口径一致。

历史问题：同一次运行里两个数字打架。

    报告顶部   47%  = 10 / 21   （分母是范围内用例总数）
    自检 SC-001 100% = 10 / 10   （分母是已执行用例数）

于是每次运行 qa-self-check 都报 high。更要紧的是 47% 这个值本身有误导性——
它把「还没跑到」和「跑失败」混在同一个分母里，既不表示质量也不表示进度。

修复：拆成两个指标。
    通过率   = 已执行中 PASS 的占比   -> 「跑过的都过了吗」
    验证覆盖 = 已执行占范围内的比例   -> 「验了多少」
SC-001 改用前者，两边口径统一。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import _check_sc001_pass_rate, _render_header_and_verdict


def _stats(**over):
    base = {
        "totalInScope": 21,
        "executedCount": 10,
        "passRate": "100%",
        "coverageRate": "48%",
        "conditionsCount": 0,
        "codeReviewCount": 0,
    }
    base.update(over)
    return base


def test_header_renders_both_metrics():
    """verdict 卡片必须同时给出通过率与验证覆盖，不能只给一个数。"""
    html = _render_header_and_verdict(
        "示例报告", {"branch": "main"}, {"status": "failed", "decision": "Incomplete"}, _stats()
    )

    assert "100%" in html, "通过率缺失"
    assert "48%" in html, "验证覆盖缺失"
    assert "10/21" in html, "覆盖卡未给出已执行/范围内 的分数"


def test_sc001_accepts_label_with_executed_count():
    """通过率标签带了「N 条已执行」括注，SC-001 仍须能读到该数字。"""
    html = '<div class="n">100%</div><div class="l">通过率（10 条已执行）</div>'
    run = {"summary": {"totalCases": 10, "casesPassed": 10}}

    assert _check_sc001_pass_rate(run, html) is None, (
        "SC-001 读不到带括注的通过率标签——正则与渲染脱节，自检会误报「字段缺失」"
    )


def test_sc001_still_detects_real_mismatch():
    """口径统一之后，真正的读数错误仍须被抓到。"""
    html = '<div class="n">47%</div><div class="l">通过率（10 条已执行）</div>'
    run = {"summary": {"totalCases": 10, "casesPassed": 10}}

    finding = _check_sc001_pass_rate(run, html)

    assert finding is not None, "报告写 47% 而执行结果 10/10，应报"
    assert finding["id"] == "SC-001"


def test_sc001_ignores_coverage_card():
    """验证覆盖卡片不能被误当成通过率。"""
    html = (
        '<div class="n">48%</div><div class="l">验证覆盖（10/21）</div>'
        '<div class="n">100%</div><div class="l">通过率（10 条已执行）</div>'
    )
    run = {"summary": {"totalCases": 10, "casesPassed": 10}}

    assert _check_sc001_pass_rate(run, html) is None
