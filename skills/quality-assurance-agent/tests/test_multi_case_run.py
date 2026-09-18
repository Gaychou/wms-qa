#!/usr/bin/env python3
"""回归测试：一次执行覆盖多条用例时，每条都要算有执行记录。

历史缺陷（逼人为了迎合门禁而拆测试）：

  evidence-integrity 门禁只按**单个** case id 匹配执行记录：

      case_id = str(task.get("sourceCaseId","")).upper()
      if case_id and case_id not in run_case_ids:
          missing_runs.append(case_id)

  而现实里一个 API 套件常常一次覆盖十几条用例。使用者把 15 条用例放在一个脚本里跑，
  `run-with-env` 推断出的 sidecar caseId 是 `OPEN-BOX-API`——于是 17 个 task 全部报
  「缺少执行记录」。

  他最后只能把套件拆开、逐条跑 15 次，E2E 也拆成两个 spec 文件分别跑，才让门禁通过。
  这属于**为了迎合门禁而改变测试组织方式**，方向是反的。

修复：sidecar 支持 `caseIds` 数组（`run-with-env --case-ids A,B,C` 声明），聚合时
一次执行计入它声明的每一条用例，门禁自然就能看到。
"""

from __future__ import annotations

import argparse
import json


def _write_sidecar(runs, *, case_id, case_ids, epoch=100, exit_code=0):
    log_name = f"run-{case_id}-suite-{epoch}.log"
    (runs / log_name).write_text("# run\n", encoding="utf-8")
    sidecar = {
        "version": "1.0",
        "runId": str(epoch),
        "caseId": case_id,
        "logFile": log_name,
        "exitCode": exit_code,
        "executedAt": "2026-01-01T00:00:00+08:00",
        "outcome": "PASS" if exit_code == 0 else "FAIL",
    }
    if case_ids is not None:
        sidecar["caseIds"] = case_ids
    (runs / f"run-{case_id}-suite-{epoch}.meta.json").write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
    )


def _runs_dir(tmp_path):
    runs = tmp_path / ".qa-agent" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    return runs


def _aggregate(qa, tmp_path):
    latest = tmp_path / "latest-run.json"
    qa.aggregate_runs(argparse.Namespace(repo=str(tmp_path), output=str(latest)))
    return json.loads(latest.read_text(encoding="utf-8"))


def _tasks(*case_ids):
    return {"tasks": [
        {"id": f"SPEC-{cid}", "sourceCaseId": cid, "priority": "P0"} for cid in case_ids
    ]}


# --- sidecar 写入与解析 ---


def test_sidecar_records_every_covered_case_id(qa, tmp_path):
    qa._record_run_sidecar(
        tmp_path, "OPEN-BOX-API", "", "suite.sh", 0, "ok", "",
        case_ids=["TC-P0-001", "TC-P0-002"],
    )

    sidecar = next((tmp_path / ".qa-agent" / "runs").glob("*.meta.json"))
    data = json.loads(sidecar.read_text(encoding="utf-8"))

    assert data["caseIds"] == ["OPEN-BOX-API", "TC-P0-001", "TC-P0-002"]


def test_parser_exposes_case_ids(qa, tmp_path):
    runs = _runs_dir(tmp_path)
    _write_sidecar(runs, case_id="A", case_ids=["A", "B"])

    parsed = qa._parse_run_sidecar(next(runs.glob("*.meta.json")))

    assert parsed["caseIds"] == ["A", "B"]


def test_legacy_sidecar_without_case_ids_still_parses(qa, tmp_path):
    """旧 sidecar 只有 caseId，必须继续可用。"""
    runs = _runs_dir(tmp_path)
    _write_sidecar(runs, case_id="A", case_ids=None)

    parsed = qa._parse_run_sidecar(next(runs.glob("*.meta.json")))

    assert parsed["caseIds"] == ["A"]


# --- 聚合 ---


def test_one_run_counts_for_every_covered_case(qa, tmp_path):
    runs = _runs_dir(tmp_path)
    _write_sidecar(runs, case_id="OPEN-BOX-API", case_ids=["OPEN-BOX-API", "TC-P0-001", "TC-P0-002"])

    data = _aggregate(qa, tmp_path)

    assert {c["caseId"] for c in data["cases"]} == {"OPEN-BOX-API", "TC-P0-001", "TC-P0-002"}
    assert data["summary"]["totalCases"] == 3


def test_end_to_end_multi_case_run_satisfies_evidence_gate(qa, tmp_path):
    """本次修复的核心：套件覆盖多条用例 → 门禁认它们都有执行记录。"""
    runs = _runs_dir(tmp_path)
    _write_sidecar(runs, case_id="OPEN-BOX-API", case_ids=["OPEN-BOX-API", "TC-P0-001", "TC-P0-002"])
    latest = _aggregate(qa, tmp_path)

    result = qa.check_evidence_integrity(
        {"cases": [{"id": "TC-P0-001"}, {"id": "TC-P0-002"}]},
        _tasks("TC-P0-001", "TC-P0-002"),
        latest,
        {},
    )

    types = [f["type"] for f in result["findings"]]
    assert "task-without-run-evidence" not in types, f"多用例执行仍被判缺证据：{types}"


def test_single_case_run_still_flags_other_cases(qa, tmp_path):
    """对照：不声明 caseIds 时，其余用例确实没有执行记录——修复前后的差别就在这里。"""
    runs = _runs_dir(tmp_path)
    _write_sidecar(runs, case_id="OPEN-BOX-API", case_ids=None)
    latest = _aggregate(qa, tmp_path)

    result = qa.check_evidence_integrity(
        {"cases": [{"id": "TC-P0-001"}, {"id": "TC-P0-002"}]},
        _tasks("TC-P0-001", "TC-P0-002"),
        latest,
        {},
    )

    types = [f["type"] for f in result["findings"]]
    assert "task-without-run-evidence" in types, "没有证据就该报，门禁不能放水"
