#!/usr/bin/env python3
"""回归测试：aggregate-runs 的逐用例执行证据必须传导到用例状态。

历史缺陷：`update_results` 读 `run_data["caseResults"]`，而 `aggregate-runs`
写的是 `run_data["cases"]`（每条带 finalOutcome），`caseResults` 全仓库没有任何
产出方。后果是每条用例的真实执行证据永远落不到用例状态上，状态只能退化成
「该层有没有在 qualityGates.commands 里配命令」——于是 run-e2e 真跑过并通过的
e2e 用例，会因为配置里 e2e 命令为空而被判成 skipped。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import update_results


def _write_case(tmp_path: Path, case_id: str, layer: str) -> Path:
    cases = {
        "version": "1.0",
        "cases": [
            {
                "id": case_id,
                "title": "示例业务用例",
                "module": "open-box",
                "type": "functional",
                "priority": "P1",
                "layer": layer,
                "automation": "automated",
                "status": "confirmed",
                "source": ["cases/open-box.json"],
                "operationPath": "用户操作路径",
                "expected": ["期望结果"],
            }
        ],
    }
    path = tmp_path / "test-cases.json"
    path.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
    return path


def _write_run(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "latest-run.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _status_of(cases_path: Path, case_id: str) -> str:
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    for case in data["cases"]:
        if case["id"] == case_id:
            return case["status"]
    raise AssertionError(f"case {case_id} not found")


def test_aggregated_pass_outcome_marks_case_passed(tmp_path):
    """aggregate-runs 产出 cases[].finalOutcome=PASS → 用例应为 passed。"""
    cases_path = _write_case(tmp_path, "TC-P1-007", "e2e")
    run_path = _write_run(
        tmp_path,
        {
            "version": "1.0",
            "summary": {"totalCases": 1},
            "cases": [{"caseId": "TC-P1-007", "finalOutcome": "PASS"}],
        },
    )

    update_results(
        argparse.Namespace(
            cases=str(cases_path),
            run=str(run_path),
            output=None,
            repo=str(tmp_path),
            legacy_gate_mapping=False,
        )
    )

    assert _status_of(cases_path, "TC-P1-007") == "passed"


def test_aggregated_fail_outcome_marks_case_failed(tmp_path):
    """finalOutcome=FAIL → 用例应为 failed。"""
    cases_path = _write_case(tmp_path, "TC-P0-001", "api")
    run_path = _write_run(
        tmp_path,
        {"cases": [{"caseId": "TC-P0-001", "finalOutcome": "FAIL"}]},
    )

    update_results(
        argparse.Namespace(
            cases=str(cases_path),
            run=str(run_path),
            output=None,
            repo=str(tmp_path),
            legacy_gate_mapping=False,
        )
    )

    assert _status_of(cases_path, "TC-P0-001") == "failed"


def test_explicit_case_results_still_take_priority(tmp_path):
    """显式 caseResults 优先级高于聚合结果，不能被覆盖。"""
    cases_path = _write_case(tmp_path, "TC-P2-001", "api")
    run_path = _write_run(
        tmp_path,
        {
            "caseResults": [{"caseId": "TC-P2-001", "status": "blocked"}],
            "cases": [{"caseId": "TC-P2-001", "finalOutcome": "PASS"}],
        },
    )

    update_results(
        argparse.Namespace(
            cases=str(cases_path),
            run=str(run_path),
            output=None,
            repo=str(tmp_path),
            legacy_gate_mapping=False,
        )
    )

    assert _status_of(cases_path, "TC-P2-001") == "blocked"


def test_unrelated_cases_untouched(tmp_path):
    """没有执行证据的用例不应被改动状态。"""
    cases_path = _write_case(tmp_path, "TC-P2-009", "api")
    run_path = _write_run(
        tmp_path,
        {"cases": [{"caseId": "TC-OTHER-999", "finalOutcome": "PASS"}]},
    )

    update_results(
        argparse.Namespace(
            cases=str(cases_path),
            run=str(run_path),
            output=None,
            repo=str(tmp_path),
            legacy_gate_mapping=False,
        )
    )

    assert _status_of(cases_path, "TC-P2-009") == "confirmed"
