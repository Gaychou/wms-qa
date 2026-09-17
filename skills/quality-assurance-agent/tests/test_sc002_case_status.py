#!/usr/bin/env python3
"""回归测试：SC-002 只该抓「有执行结果却没渲染出来」，不该抓「本轮没跑到」。

原判据是数徽章总数：

    confirmed_badges = 报告里 confirmed 徽章数
    passed = latest-run.json 的 casesPassed
    if confirmed_badges > 0 and passed > 0: 报 high

但 confirmed 徽章只在「该用例没有 run」时出现——那是合法状态（本轮没跑到它）。
只要一次运行是部分执行（21 条里验了 10 条），原判据必然误报。

更麻烦的是它给出的 fix：一律改用 finalOutcome 渲染。照做会让未执行用例的状态列
变空，把「这条没跑过」这个事实藏起来——渲染正确性 与 执行完整性 是两件事。

新判据逐用例核对：该用例有 finalOutcome 时，它的那一行就必须展示对应的执行结果。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import _check_sc002_case_status


def _row(case_id: str, badge: str, title: str = "示例用例") -> str:
    """按 _render_case_row 的真实形态造一行。"""
    return (
        f'<details class="case-row" id="{case_id}">'
        f'<summary><span><code>{case_id}</code></span>'
        f'<span><span class="b warn">P1</span></span>'
        f'<span>{badge}</span>'
        f'<span class="ctitle">{title}</span>'
        f'<span class="clayer">api</span><span class="cruns">1</span>'
        f'</summary><div class="body">…</div></details>'
    )


def _run(*case_outcomes) -> dict:
    """按 aggregate-runs 的真实产物形态造 latest-run.json。

    必须带上 summary.casesPassed —— 旧判据正是读这个字段来判「存在 PASS」的，
    漏掉它会让旧判据恒为 0，测试就以「恰好通过」的姿态掩盖回归。
    """
    cases = [{"caseId": cid, "finalOutcome": out} for cid, out in case_outcomes]
    passed = sum(1 for _, out in case_outcomes if str(out).upper() == "PASS")
    return {"summary": {"totalCases": len(cases), "casesPassed": passed}, "cases": cases}


def test_partial_execution_is_not_a_finding():
    """部分执行：有 run 的显示 PASS，没 run 的显示 confirmed —— 不该报。"""
    html = (
        _row("TC-P1-007", '<span class="b passed">PASS</span>')
        + _row("TC-P1-008", '<span class="b mute">confirmed</span>')
    )
    run = _run(("TC-P1-007", "PASS"))  # 只有 007 有 run；008 没跑到

    assert _check_sc002_case_status(html, run) is None, (
        "部分执行被误报——confirmed 徽章在「该用例没有 run」时是合法状态"
    )


def test_case_with_run_rendered_as_lifecycle_status_is_a_finding():
    """该用例有 run 却渲染成 confirmed —— 这才是真渲染 bug。"""
    html = _row("TC-P1-007", '<span class="b mute">confirmed</span>')
    run = _run(("TC-P1-007", "PASS"))

    finding = _check_sc002_case_status(html, run)

    assert finding is not None, "有执行结果却渲染成生命周期状态，应报"
    assert finding["id"] == "SC-002"
    assert "TC-P1-007" in finding["summary"]


def test_fail_outcome_also_must_render():
    """FAIL 同样必须渲染，不能只认 PASS。"""
    html = _row("TC-P0-001", '<span class="b mute">confirmed</span>')
    run = _run(("TC-P0-001", "FAIL"))

    assert _check_sc002_case_status(html, run) is not None


def test_all_executed_and_rendered_is_clean():
    """全部执行且都渲染正确 —— 不该报。"""
    html = (
        _row("TC-P0-001", '<span class="b passed">PASS</span>')
        + _row("TC-P0-002", '<span class="b failed">FAIL</span>')
    )
    run = _run(("TC-P0-001", "PASS"), ("TC-P0-002", "FAIL"))

    assert _check_sc002_case_status(html, run) is None


def test_no_runs_at_all_is_clean():
    """一条都没跑：全是 confirmed —— 那是事实，不是渲染 bug。"""
    html = _row("TC-P0-001", '<span class="b mute">confirmed</span>')

    assert _check_sc002_case_status(html, {"cases": []}) is None
