#!/usr/bin/env python3
"""金样测试：在临时仓库上跑真实 pipeline，断言「生产者 → 消费者」契约不破。

为什么需要这个文件
------------------
本仓库的单元测试大多用手写 fixture，测的是「我以为的产物形状」。而 2026-09-17
对一个真实业务项目做全流程验收时捞出的 4 个缺陷，全部是「生产者真实输出 → 消费者
解析失败」，手写 fixture 一个都拦不住：

  1. assert-oracle-mapping 调用了未定义的 logger，成功/失败两条路径都抛 NameError
  2. 同一个门禁读 task["traceability"]（这是**用例**的字段），而真实生成器把风险
     关联写在 oracle 各项的 sourceRiskId 上 —— 门禁因此恒判失败
  3. _render_code_review 按另一套 schema 读产物：把字符串 summary 当字典读（崩溃）、
     finding 标题读 summary 而契约字段是 title（渲染空标题）、证据读 failureScenario
     而契约字段是 evidence
  4. update-results 读 run_data["caseResults"]，而 aggregate-runs 写的是
     run_data["cases"]（caseResults 全仓库没有任何产出方）—— 真实执行证据因此永远
     落不到用例状态上

共同点：单元测试里手写的 fixture 恰好带了真实产物**没有**的字段（例如给 spec task
手写 traceability），于是测试全绿而产品是坏的。

做法
----
不用手写 fixture：先跑真实的生产者命令，再从它的**真实产出**里派生后续输入。
生产链全程确定性、零 LLM 调用，可在 CI 离线跑，单次约 2 秒。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
QA = str((SCRIPTS / "qa_agent.py").resolve())

# 触发 analyze-risks 的资金/权限/异步规则的源码片段
SRC = """public class PayService {
    // deduct balance, write balance log, callback notify, permission check
    public void deduct(Long userId, java.math.BigDecimal amount) { }
    public void refund(Long userId, java.math.BigDecimal amount) { }
}
"""


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """在 repo 下执行 qa_agent.py，返回完整结果（不抛异常，由调用方断言）。"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, QA, *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        errors="replace",
        env=env,
    )


def _out(proc: subprocess.CompletedProcess) -> str:
    return f"exit={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"


@pytest.fixture()
def project(tmp_path: Path):
    """最小可跑仓库：一个含资金关键词的源文件 + 项目标识，且是个 git 仓库。"""
    repo = tmp_path / "repo"
    (repo / "src/main/java/com/demo").mkdir(parents=True)
    (repo / "src/main/java/com/demo/PayService.java").write_text(SRC, encoding="utf-8")
    (repo / "package.json").write_text('{"name":"demo","version":"1.0.0"}', encoding="utf-8")
    (repo / ".qa-agent/cases").mkdir(parents=True)

    def git(*a: str) -> None:
        subprocess.run(["git", *a], cwd=str(repo), capture_output=True, text=True)

    git("init", "-q")
    git("add", "-A")
    git("-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "init")

    current = repo / ".qa-agent" / "current"
    current.mkdir(parents=True, exist_ok=True)
    return repo, current


def _derive_risks(repo: Path, current: Path) -> list[dict]:
    """跑上游三个阶段，返回 analyze-risks 的**真实**产出。"""
    for args, label in [
        (("collect-context", "--repo", ".", "--scope", "head",
          "--output", str(current / "context.json")), "collect-context"),
        (("index-existing-cases", "--repo", ".",
          "--output", str(current / "existing-case-index.json")), "index-existing-cases"),
        (("analyze-risks", "--repo", ".",
          "--context", str(current / "context.json"),
          "--existing-index", str(current / "existing-case-index.json"),
          "--output", str(current / "risk-analysis.json")), "analyze-risks"),
    ]:
        proc = _run(repo, *args)
        assert proc.returncode == 0, f"{label} 失败：{_out(proc)}"

    return json.loads((current / "risk-analysis.json").read_text(encoding="utf-8"))["risks"]


def _write_cases(repo: Path, risks: list[dict]) -> Path:
    """为每条风险派生一个用例——断言内容直接取自风险的真实 requiredAssertions。

    这样生成出来的 oracle 会带上 sourceRiskId 与同样的断言文本，
    门禁理应判定「已覆盖」。修复前它必然判失败（找不到任务级 traceability）。
    """
    cases = []
    for i, risk in enumerate(risks, start=1):
        cases.append({
            "id": f"TC-P0-{i:03d}",
            "title": f"业务用例 {i}",
            "module": "demo",
            "type": "functional",
            "priority": risk.get("priority") or "P1",
            "layer": "api",
            "automation": "automated",
            "status": "confirmed",
            "source": ["prd/demo.md"],
            "operationPath": "用户在示例页面发起操作并观察结果",
            "expected": list(risk.get("requiredAssertions") or []),
            "traceability": [risk["id"]],
            "businessAssertions": list(risk.get("requiredAssertions") or []),
        })
    path = repo / ".qa-agent" / "cases" / "demo.json"
    path.write_text(json.dumps({"version": "1.0", "cases": cases}, ensure_ascii=False),
                    encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# 契约测试
# --------------------------------------------------------------------------

def test_generate_spec_tasks_emits_oracle_source_risk_id(project):
    """生产者契约：风险关联必须落在 oracle 各项的 sourceRiskId 上。

    这是消费者（assert-oracle-mapping / 报告渲染）唯一能读到的关联。
    曾经只有用例级的 traceability，任务上没有，消费者因此永远匹配不到。
    """
    repo, current = project
    risks = _derive_risks(repo, current)
    assert risks, "fixture 未产出任何风险，测试前提不成立"

    cases_path = _write_cases(repo, risks)
    proc = _run(repo, "generate-spec-tasks", "--cases", str(cases_path), "--repo", ".",
                "--output", str(current / "test-spec-tasks.json"))
    assert proc.returncode == 0, _out(proc)

    tasks = json.loads((current / "test-spec-tasks.json").read_text(encoding="utf-8"))["tasks"]
    risk_ids = {r["id"] for r in risks}

    linked = set()
    for task in tasks:
        for items in (task.get("oracle") or {}).values():
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and item.get("sourceRiskId"):
                    linked.add(item["sourceRiskId"])

    assert linked & risk_ids, (
        "没有任何 spec task 的 oracle 携带 sourceRiskId——"
        "消费者按任务级 traceability 匹配的写法将永远判失败。"
        f"（tasks={len(tasks)}）"
    )


def test_oracle_mapping_gate_resolves_risk_link(project):
    """消费者契约：覆盖全部风险后，门禁应当通过。

    判别力：修复前匹配器读 task["traceability"]（生成器不产出该字段），
    即使每条风险的断言都已进入 oracle 也一律判失败。修复后应当通过。
    """
    repo, current = project
    risks = _derive_risks(repo, current)
    assert risks, "fixture 未产出任何风险，测试前提不成立"

    cases_path = _write_cases(repo, risks)
    proc = _run(repo, "generate-spec-tasks", "--cases", str(cases_path), "--repo", ".",
                "--output", str(current / "test-spec-tasks.json"))
    assert proc.returncode == 0, _out(proc)

    check_path = current / "oracle-mapping-check.json"
    proc = _run(repo, "assert-oracle-mapping",
                "--risk-analysis", str(current / "risk-analysis.json"),
                "--spec-tasks", str(current / "test-spec-tasks.json"),
                "--output", str(check_path))

    # 无论通过与否，都不得是崩溃（历史上这里抛 NameError: logger is not defined）
    assert "Traceback" not in proc.stderr, f"门禁崩溃而非给出结论：{_out(proc)}"

    result = json.loads(check_path.read_text(encoding="utf-8"))
    assert result.get("status") == "passed", (
        "已覆盖全部风险却仍判失败，说明生产者与消费者的风险关联口径不一致："
        f"{json.dumps(result.get('findings'), ensure_ascii=False)}"
    )


def test_render_report_accepts_contract_shaped_artifacts(project):
    """渲染契约：按文档 schema 产出的产物必须能渲染，不得崩溃。

    历史上 _render_code_review 把字符串 summary 当字典读，直接 AttributeError
    打挂整份报告——而 references/code-review.md 定义的 summary 就是字符串。
    """
    repo, current = project
    risks = _derive_risks(repo, current)
    cases_path = _write_cases(repo, risks)

    proc = _run(repo, "generate-spec-tasks", "--cases", str(cases_path), "--repo", ".",
                "--output", str(current / "test-spec-tasks.json"))
    assert proc.returncode == 0, _out(proc)

    # 严格照 references/code-review.md 的形状：summary 是字符串，finding 用 title/evidence
    (current / "code-review.json").write_text(json.dumps({
        "status": "failed",
        "summary": "一句话结论（契约里 summary 是字符串）",
        "scope": {"files": ["src/main/java/com/demo/PayService.java"], "description": "示例模块"},
        "findings": [{
            "id": "CR-001",
            "severity": "P1",
            "file": "src/main/java/com/demo/PayService.java",
            "line": 3,
            "title": "扣减缺少幂等保护",
            "evidence": "第 3 行未见去重键",
            "recommendation": "增加幂等键",
        }],
        "residualRisks": [],
        "deferredFindings": [],
    }, ensure_ascii=False), encoding="utf-8")

    report = current.parent / "reports" / "latest-report.html"
    report.parent.mkdir(parents=True, exist_ok=True)

    proc = _run(repo, "render-report",
                "--cases", str(cases_path),
                "--spec-tasks", str(current / "test-spec-tasks.json"),
                "--risk-analysis", str(current / "risk-analysis.json"),
                "--code-review", str(current / "code-review.json"),
                "--title", "金样测试报告",
                "--output", str(report))

    assert "Traceback" not in proc.stderr, f"渲染崩溃：{_out(proc)}"
    assert proc.returncode == 0, _out(proc)

    html = report.read_text(encoding="utf-8", errors="replace")
    # 契约字段必须真的渲染出来，而不是空白
    assert "扣减缺少幂等保护" in html, "finding 标题未渲染——标题字段口径不一致"
    assert "第 3 行未见去重键" in html, "finding 证据未渲染——证据字段口径不一致"


def _advance_to_report(repo: Path, current: Path) -> Path:
    """把链路推到 render-report：执行证据 → 门禁 → 代码审查 → 渲染报告。

    产出真实形状的全部产物，供渲染层消费。任何一步失败都直接断言出来，
    避免后续章节断言因为「上游产物根本没生成」而变成假阳性。
    """
    risks = _derive_risks(repo, current)
    cases_path = _write_cases(repo, risks)

    proc = _run(repo, "generate-spec-tasks", "--cases", str(cases_path), "--repo", ".",
                "--output", str(current / "test-spec-tasks.json"))
    assert proc.returncode == 0, f"generate-spec-tasks 失败：{_out(proc)}"

    # 逐用例执行证据：让用例矩阵真的渲染出 PASS
    runs_dir = repo / ".qa-agent" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    for i, case in enumerate(cases):
        run_id = str(1_800_000_000 + i)
        log_name = f"run-{case['id'].lower()}-{run_id}.log"
        (runs_dir / log_name).write_text(
            f"case: {case['id']}\noutcome: PASS\n", encoding="utf-8"
        )
        (runs_dir / f"run-{case['id'].lower()}-{run_id}.meta.json").write_text(
            json.dumps({
                "version": "1.0", "runId": run_id, "caseId": case["id"], "taskId": "",
                "script": "mvn test", "logFile": log_name, "exitCode": 0,
                "executedAt": "2026-09-17T10:00:00+08:00", "outcome": "PASS",
            }, ensure_ascii=False), encoding="utf-8")

    steps = [
        (("aggregate-runs", "--repo", ".", "--output", str(current / "latest-run.json")), "aggregate-runs"),
        (("update-results", "--cases", str(cases_path), "--run", str(current / "latest-run.json")), "update-results"),
        (("assert-completion", "--cases", str(cases_path),
          "--spec-tasks", str(current / "test-spec-tasks.json"),
          "--priorities", "P0,P1", "--min-specs-by-priority", "P0=1,P1=1",
          "--output", str(current / "completion-check.json")), "assert-completion"),
    ]
    for args, label in steps:
        proc = _run(repo, *args)
        # assert-completion 判失败是合法结论，但不得崩溃
        assert "Traceback" not in proc.stderr, f"{label} 崩溃：{_out(proc)}"

    # 按契约形状写 code-review（summary 是字符串，finding 用 title/evidence）
    (current / "code-review.json").write_text(json.dumps({
        "status": "failed",
        "summary": "一句话结论（契约里 summary 是字符串）",
        "scope": {"files": ["src/main/java/demo/PayService.java"], "description": "示例模块"},
        "findings": [{
            "id": "CR-001", "severity": "P1",
            "file": "src/main/java/demo/PayService.java", "line": 3,
            "title": "扣减缺少幂等保护", "evidence": "第 3 行未见去重键",
            "recommendation": "增加幂等键",
        }],
        "residualRisks": [], "deferredFindings": [],
    }, ensure_ascii=False), encoding="utf-8")

    report = current.parent / "reports" / "latest-report.html"
    report.parent.mkdir(parents=True, exist_ok=True)
    proc = _run(repo, "render-report",
                "--cases", str(cases_path),
                "--run", str(current / "latest-run.json"),
                "--spec-tasks", str(current / "test-spec-tasks.json"),
                "--completion-check", str(current / "completion-check.json"),
                "--risk-analysis", str(current / "risk-analysis.json"),
                "--code-review", str(current / "code-review.json"),
                "--title", "金样测试报告",
                "--output", str(report))
    assert "Traceback" not in proc.stderr, f"渲染崩溃：{_out(proc)}"
    assert proc.returncode == 0, _out(proc)
    return report


def test_report_sections_render_actual_content(project):
    """渲染契约：报告的每个章节都要真的渲染出内容，不能只剩标题。

    这条覆盖 render 层的全部函数——其中大多数与 _render_code_review 一样是从
    别的项目整段搬来的（代码里留有 "from project" 标记），照着另一套产物形状写，
    跟本项目的契约从没对过。_render_code_review 已经因此炸过一次（把字符串
    summary 当字典读）。

    只断言「不崩溃」是不够的：读错字段往往不报错，只是安静地渲染成空白。
    所以每一节都断言一个只有该节数据才能带出来的具体字符串。
    """
    repo, current = project
    report = _advance_to_report(repo, current)
    html = report.read_text(encoding="utf-8", errors="replace")

    risks = json.loads((current / "risk-analysis.json").read_text(encoding="utf-8"))["risks"]
    cases = json.loads((repo / ".qa-agent" / "cases" / "demo.json").read_text(encoding="utf-8"))["cases"]

    expectations = [
        ("执行摘要", ["本轮范围", "本次交付"]),
        ("验收门禁", ["验收完备度"]),
        ("代码审查", ["扣减缺少幂等保护", "第 3 行未见去重键"]),
        ("风险与覆盖缺口", ["风险明细", risks[0]["id"]]),
        ("用例矩阵", ["用例矩阵", cases[0]["id"]]),
        ("附录", ["附录"]),
    ]
    for section, probes in expectations:
        assert section in html, f"报告缺少章节「{section}」"
        for probe in probes:
            assert probe in html, f"章节「{section}」未渲染出内容：{probe!r}"

    # verdict 卡片的两个指标都要在，且不能互相替代
    assert "通过率" in html, "verdict 卡片缺少通过率"
    assert "验证覆盖" in html, "verdict 卡片缺少验证覆盖"


def test_update_results_consumes_aggregate_runs_output(project):
    """证据链契约：aggregate-runs 的产出必须能被 update-results 消费。

    历史上 update-results 读 caseResults，而 aggregate-runs 写 cases，
    导致真实执行证据永远落不到用例状态上。
    """
    repo, current = project
    risks = _derive_risks(repo, current)
    cases_path = _write_cases(repo, risks)

    run_path = current / "latest-run.json"
    run_path.write_text(json.dumps({
        "version": "1.0",
        "summary": {"totalCases": 1, "casesPassed": 1},
        "cases": [{"caseId": "TC-P0-001", "finalOutcome": "PASS"}],
        "unmatchedLogs": [],
    }, ensure_ascii=False), encoding="utf-8")

    proc = _run(repo, "update-results", "--cases", str(cases_path), "--run", str(run_path))
    assert proc.returncode == 0, _out(proc)

    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    status = next(c["status"] for c in cases if c["id"] == "TC-P0-001")
    assert status == "passed", (
        f"聚合产出的逐用例执行证据未传导到用例状态（当前 {status}）——"
        "消费者读的键与 aggregate-runs 写出的键不一致"
    )
