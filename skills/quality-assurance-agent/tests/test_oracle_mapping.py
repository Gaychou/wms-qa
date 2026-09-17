#!/usr/bin/env python3
"""测试 oracle 传导门禁：风险 requiredAssertions → spec-task oracle 的覆盖判定。

判据是「覆盖」，不是「文本等价」——这一点是踩过坑才定下来的：

风险侧产出的是抽象业务类目（「金额计算正确」），任务侧 oracle 断言是具体到实现的
说法（「余额扣减金额与商品单价一致」）。两者语义等价、用词不同。早期实现做精确
子串匹配，于是对任何真实产物都恒判失败，门禁形同虚设。

现在的判据：每条 P0/P1 风险至少要有一条携带其 sourceRiskId 的 oracle 断言。
断言内容是否等价属于人的判断，交给代码审查。
"""

import argparse
import json
import sys
from pathlib import Path

import pytest

# Add parent directory to path for qa_agent import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import assert_oracle_mapping, assert_oracle_mapping_data


def _task(oracle_items, risk_id, **over):
    """造一个带 sourceRiskId 关联的 spec task。"""
    task = {
        "id": "SPEC-TC-P0-001-API-001",
        "sourceCaseId": "TC-P0-001",
        "assertions": [i["assertion"] for i in oracle_items],
        "oracle": {
            "api": oracle_items,
            "db": [],
            "ui": [],
            "sideEffects": [],
            "negativeAssertions": [],
        },
    }
    if risk_id:
        for item in task["oracle"]["api"]:
            item["sourceRiskId"] = risk_id
    task.update(over)
    return task


def _risk(risk_id="RISK-P0-001", priority="P0", assertions=None):
    return {
        "risks": [
            {
                "id": risk_id,
                "priority": priority,
                "category": "money-reward-settlement",
                "requiredAssertions": assertions or ["金额计算正确", "重复结算状态一致"],
            }
        ]
    }


def test_covered_risk_passes():
    """风险有 oracle 断言关联 → 通过。"""
    result = assert_oracle_mapping_data(
        _risk(),
        {"tasks": [_task([{"type": "api", "assertion": "余额扣减正确"}], "RISK-P0-001")]},
    )

    assert result["status"] == "passed"
    assert result["summary"]["unmappedCount"] == 0


def test_uncovered_risk_fails():
    """该 P0/P1 风险没有任何任务关联它 → 失败。这才是可行动的信号。"""
    result = assert_oracle_mapping_data(
        _risk("RISK-P1-009", "P1"),
        {"tasks": [_task([{"type": "api", "assertion": "别的断言"}], "RISK-P0-001")]},
    )

    assert result["status"] == "failed"
    finding = result["findings"][0]
    assert finding["riskId"] == "RISK-P1-009"
    assert "完全没有覆盖" in finding["message"]
    assert finding["requiredAssertions"] == ["金额计算正确", "重复结算状态一致"]


def test_abstract_vs_concrete_wording_passes():
    """风险断言与任务断言用词不同但语义对应 → 通过，不再因文本不匹配而误杀。

    这是本门禁判据变更的核心：风险侧「金额计算正确」 vs 任务侧
    「余额扣减金额与商品单价一致」，精确子串永远不相等。
    """
    risk = _risk(assertions=["金额计算正确", "重复提交不重复发放"])
    task = _task(
        [
            {"type": "api", "assertion": "余额扣减金额与商品单价一致"},
            {"type": "api", "assertion": "同款重复提交只扣一次"},
        ],
        "RISK-P0-001",
    )

    result = assert_oracle_mapping_data(risk, {"tasks": [task]})

    assert result["status"] == "passed", (
        "用词不同但已显式关联的风险被判失败——门禁又退回了文本匹配"
    )


def test_text_match_is_recorded_but_not_used_as_verdict():
    """文本命中的情况仍记录在 assertionTextMatch 里，供审查参考。"""
    risk = _risk(assertions=["完全不在任务文本里的断言"])
    task = _task([{"type": "api", "assertion": "余额扣减正确"}], "RISK-P0-001")

    result = assert_oracle_mapping_data(risk, {"tasks": [task]})

    assert result["status"] == "passed", "关联存在即通过，文本不匹配不影响判定"


def test_risk_without_required_assertions_is_skipped():
    """没有 requiredAssertions 的风险没有可校验的内容，不参与判定也不计入检查数。"""
    result = assert_oracle_mapping_data(
        {"risks": [{"id": "RISK-P0-001", "priority": "P0", "requiredAssertions": []}]},
        {"tasks": []},
    )

    assert result["status"] == "passed", "无可校验内容的风险不该被判未覆盖"
    assert result["summary"]["totalRisksChecked"] == 0
    assert result["findings"] == []


def test_p2_risks_are_not_enforced():
    """只强制 P0/P1。"""
    result = assert_oracle_mapping_data(
        _risk("RISK-P2-006", "P2"), {"tasks": []}
    )

    assert result["status"] == "passed"
    assert result["summary"]["totalRisksChecked"] == 0


def test_cli_fails_cleanly(tmp_path):
    """门禁判失败时必须抛 SystemExit(1)，而不是 NameError 崩溃。

    回归测试：曾经调用未定义的 logger，成功与失败两条路径都会抛 NameError，
    把「门禁未通过」这个业务结论淹没在栈里。
    """
    risk_file = tmp_path / "risk.json"
    tasks_file = tmp_path / "tasks.json"
    out_file = tmp_path / "out.json"
    risk_file.write_text(json.dumps(_risk("RISK-P1-003", "P1"), ensure_ascii=False), encoding="utf-8")
    tasks_file.write_text(json.dumps({"tasks": []}, ensure_ascii=False), encoding="utf-8")

    args = argparse.Namespace(
        risk_analysis=str(risk_file), spec_tasks=str(tasks_file), output=str(out_file)
    )

    with pytest.raises(SystemExit) as exc:
        assert_oracle_mapping(args)
    assert exc.value.code == 1
    assert out_file.exists()


def test_cli_passes_cleanly(tmp_path):
    """门禁通过时也走 print 路径，不得崩溃（同一处 logger 缺陷的另一条分支）。"""
    risk_file = tmp_path / "risk.json"
    tasks_file = tmp_path / "tasks.json"
    out_file = tmp_path / "out.json"
    risk_file.write_text(json.dumps(_risk(), ensure_ascii=False), encoding="utf-8")
    tasks_file.write_text(
        json.dumps({"tasks": [_task([{"type": "api", "assertion": "余额扣减正确"}], "RISK-P0-001")]},
                   ensure_ascii=False),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        risk_analysis=str(risk_file), spec_tasks=str(tasks_file), output=str(out_file)
    )
    assert_oracle_mapping(args)  # 不抛异常

    assert json.loads(out_file.read_text(encoding="utf-8"))["status"] == "passed"
