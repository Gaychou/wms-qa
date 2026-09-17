#!/usr/bin/env python3
"""回归测试：按需产出的报告源缺失，不应判为报告陈旧。

历史问题：assert-report-freshness 只要收到 --cases，就无条件要求同目录存在
test-cases.generated.json，缺失即 source-missing / Not Ready。

但该文件只在「本轮重新生成用例」那条路径上产出；而复用已 promote 的用例集
（.qa-agent/cases/*.json → current/test-cases.json，promote-cases 的设计意图）
时本来就没有它——回归运行恰恰是这个场景。结果是任何复用路径的运行永远判
Not Ready，时效门禁形同虚设。

修复只放宽「缺失」：文件若存在却比报告新，仍按陈旧拦截。
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import assert_report_freshness


def _setup(tmp_path: Path) -> tuple[Path, Path, Path]:
    """造出报告 + 用例，返回 (report, cases, generated)。"""
    report = tmp_path / "latest-report.html"
    cases = tmp_path / "test-cases.json"
    generated = tmp_path / "test-cases.generated.json"

    report.write_text("<html>报告</html>", encoding="utf-8")
    cases.write_text(json.dumps({"version": "1.0", "cases": []}), encoding="utf-8")
    return report, cases, generated


def _run(report: Path, cases: Path, out: Path, **extra) -> dict:
    """跑门禁并返回产物。门禁判失败时会 raise SystemExit(1)，产物在此之前已落盘。"""
    try:
        assert_report_freshness(
            argparse.Namespace(report=str(report), cases=str(cases), output=str(out), **extra)
        )
    except SystemExit:
        pass
    return json.loads(out.read_text(encoding="utf-8"))


def test_missing_generated_cases_is_not_stale(tmp_path):
    """复用已 promote 用例集时没有 test-cases.generated.json，不该判陈旧。"""
    report, cases, generated = _setup(tmp_path)
    assert not generated.exists()

    result = _run(report, cases, tmp_path / "freshness.json")

    assert result["status"] == "passed", (
        "缺失按需产出的源被判成陈旧——复用已 promote 用例集的运行将永远 Not Ready："
        f"{json.dumps(result.get('findings'), ensure_ascii=False)}"
    )
    entry = next(e for e in result["sourceFiles"] if e["label"] == "generated-cases")
    assert entry.get("optional") is True, "可选源应在产物里标记出来，便于追溯"


def test_present_but_newer_generated_cases_still_fails(tmp_path):
    """该文件存在却比报告新 —— 这才是真陈旧，必须拦。"""
    report, cases, generated = _setup(tmp_path)
    generated.write_text(json.dumps({"version": "1.0", "cases": []}), encoding="utf-8")
    future = time.time() + 60
    os.utime(generated, (future, future))

    result = _run(report, cases, tmp_path / "freshness.json")

    assert result["status"] == "failed"
    assert any(f["type"] == "stale-source" for f in result["findings"])


def test_missing_required_source_still_fails(tmp_path):
    """非按需的源缺失仍必须判失败，不能把放宽做过了头。"""
    report, cases, _ = _setup(tmp_path)
    missing = tmp_path / "risk-analysis.json"

    result = _run(report, cases, tmp_path / "f2.json", risk_analysis=str(missing))

    assert result["status"] == "failed"
    assert any(
        f["type"] == "source-missing" and f["source"] == "risk-analysis"
        for f in result["findings"]
    ), "必要的源缺失必须仍然拦截"
