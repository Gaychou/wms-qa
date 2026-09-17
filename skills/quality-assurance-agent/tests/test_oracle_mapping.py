#!/usr/bin/env python3
"""测试 oracle 传导机制：风险 requiredAssertions → spec-task oracle 字段的映射"""

import argparse
import json
import sys
from pathlib import Path

import pytest

# Add parent directory to path for qa_agent import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import assert_oracle_mapping_data


def test_assert_oracle_mapping_basic():
    """测试基础 oracle 映射：风险的 requiredAssertions 必须出现在某个 task 的 oracle/assertions 中"""
    risk_data = {
        "risks": [
            {
                "id": "RISK-P0-001",
                "priority": "P0",
                "category": "money-reward-settlement",
                "requiredAssertions": ["余额扣减正确", "流水记录完整"],
                "requiresE2E": False,
            }
        ]
    }
    spec_tasks = {
        "tasks": [
            {
                "id": "SPEC-TC-P0-001-API-001",
                "sourceCaseId": "TC-P0-001",
                "assertions": ["余额扣减正确"],
                "oracle": {
                    "api": [],
                    "db": [
                        {
                            "type": "db",
                            "assertion": "余额扣减正确",
                            "sourceRiskId": "RISK-P0-001",
                        },
                        {
                            "type": "db",
                            "assertion": "流水记录完整",
                            "sourceRiskId": "RISK-P0-001",
                        },
                    ],
                    "ui": [],
                    "sideEffects": [],
                    "negativeAssertions": [],
                },
                "traceability": ["RISK-P0-001"],
            }
        ]
    }

    # Should pass: all requiredAssertions are in oracle.db
    result = assert_oracle_mapping_data(risk_data, spec_tasks)
    assert result["status"] == "passed", f"Expected passed, got {result}"
    assert len(result["findings"]) == 0
    assert result["summary"]["unmappedCount"] == 0


def test_assert_oracle_mapping_missing():
    """测试缺失 oracle 映射：某个风险的断言在所有 task 中都找不到"""
    risk_data = {
        "risks": [
            {
                "id": "RISK-P1-005",
                "priority": "P1",
                "category": "data-integrity",
                "requiredAssertions": ["概率区间[0,1)全覆盖无gap"],
                "requiresE2E": False,
            }
        ]
    }
    spec_tasks = {
        "tasks": [
            {
                "id": "SPEC-TC-P2-014-API-001",
                "sourceCaseId": "TC-P2-014",
                "assertions": ["商品配置返回正确"],
                "oracle": {
                    "api": [{"type": "api", "assertion": "接口状态码200"}],
                    "db": [],  # requiredAssertions 的 db 断言没有传导到这里
                    "ui": [],
                    "sideEffects": [],
                    "negativeAssertions": [],
                },
                "traceability": ["RISK-P1-005"],
            }
        ]
    }

    # Should fail: requiredAssertions not in any task's oracle
    result = assert_oracle_mapping_data(risk_data, spec_tasks)
    assert result["status"] == "failed"
    assert len(result["findings"]) == 1
    assert result["findings"][0]["riskId"] == "RISK-P1-005"
    assert "概率区间[0,1)全覆盖无gap" in result["findings"][0]["missingAssertions"]


def test_assert_oracle_mapping_partial():
    """测试部分映射：风险有 3 个断言，只映射了 2 个"""
    risk_data = {
        "risks": [
            {
                "id": "RISK-P0-002",
                "priority": "P0",
                "category": "state-machine",
                "requiredAssertions": [
                    "asset_status 0→1",
                    "open_type=2",
                    "无余额流水",
                ],
                "requiresE2E": False,
            }
        ]
    }
    spec_tasks = {
        "tasks": [
            {
                "id": "SPEC-TC-P0-003-API-001",
                "sourceCaseId": "TC-P0-003",
                "assertions": ["asset_status 0→1", "open_type=2"],
                "oracle": {
                    "api": [],
                    "db": [
                        {"type": "db", "assertion": "asset_status 0→1"},
                        {"type": "db", "assertion": "open_type=2"},
                        # Missing: 无余额流水
                    ],
                    "ui": [],
                    "sideEffects": [],
                    "negativeAssertions": [],
                },
                "traceability": ["RISK-P0-002"],
            }
        ]
    }

    # Should fail: one assertion missing
    result = assert_oracle_mapping_data(risk_data, spec_tasks)
    assert result["status"] == "failed"
    assert len(result["findings"]) == 1
    assert "无余额流水" in result["findings"][0]["missingAssertions"]
    assert len(result["findings"][0]["missingAssertions"]) == 1  # Only the missing one


def test_maps_risk_through_oracle_source_risk_id():
    """回归测试：风险关联在 oracle 各项的 sourceRiskId 上，不在任务级 traceability 上。

    真实生成器（generate-spec-tasks）产出的任务**没有** traceability 字段——
    那是用例（cases[]）的字段。匹配器原先只读 task["traceability"]，导致真实链路
    106/106 任务 0 命中，门禁恒判失败。上面的用例手写了 traceability，所以测试
    全绿而产品是坏的。
    """
    risk_data = {
        "risks": [
            {
                "id": "RISK-P0-001",
                "priority": "P0",
                "category": "money-reward-settlement",
                "requiredAssertions": ["余额扣减正确", "流水记录完整"],
            }
        ]
    }
    spec_tasks = {
        "tasks": [
            {
                "id": "SPEC-TC-P0-001-API-001",
                "sourceCaseId": "TC-P0-001",
                "assertions": [],
                "oracle": {
                    "api": [
                        {"type": "api", "assertion": "余额扣减正确", "sourceRiskId": "RISK-P0-001"}
                    ],
                    "db": [
                        {"type": "db", "assertion": "流水记录完整", "sourceRiskId": "RISK-P0-001"}
                    ],
                    "ui": [],
                    "sideEffects": [],
                    "negativeAssertions": [],
                },
                # 刻意不写 traceability —— 与真实生成器产物一致
            }
        ]
    }

    result = assert_oracle_mapping_data(risk_data, spec_tasks)
    assert result["status"] == "passed", f"Expected passed, got {result}"
    assert result["summary"]["unmappedCount"] == 0


def test_assert_oracle_mapping_cli_fails_cleanly(tmp_path):
    """回归测试：门禁判定失败时必须抛 SystemExit(1)，而不是 NameError 崩溃。

    曾因调用未定义的 logger，成功与失败两条路径都会抛 NameError，
    把「门禁未通过」这个业务结论淹没在栈里。
    """
    from qa_agent import assert_oracle_mapping

    risk_file = tmp_path / "risk.json"
    tasks_file = tmp_path / "tasks.json"
    out_file = tmp_path / "out.json"
    risk_file.write_text(
        json.dumps(
            {
                "risks": [
                    {
                        "id": "RISK-P0-001",
                        "priority": "P0",
                        "requiredAssertions": ["永远不会被映射的断言"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    tasks_file.write_text(json.dumps({"tasks": []}, ensure_ascii=False), encoding="utf-8")

    args = argparse.Namespace(
        risk_analysis=str(risk_file), spec_tasks=str(tasks_file), output=str(out_file)
    )

    with pytest.raises(SystemExit) as exc:
        assert_oracle_mapping(args)
    assert exc.value.code == 1
    assert out_file.exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
