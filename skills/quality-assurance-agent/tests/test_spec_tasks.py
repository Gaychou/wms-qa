"""Task 3: Spec-task generation and oracle mapping."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _minimal_cases(cases: list[dict]) -> dict:
    return {"status": "confirmed", "version": "1.0", "cases": cases}


def _minimal_case(case_id="TC-P0-001", priority="P0", **extra) -> dict:
    base = {
        "id": case_id,
        "priority": priority,
        "title": "下单 API",
        "module": "order",
        "type": "business",
        "layer": "api",
        "automation": "automated",
        "status": "confirmed",
        "businessActor": "普通用户",
        "operationPath": "POST /order/create",
        "preconditions": ["余额充足"],
        "steps": ["发起下单"],
        "expected": ["下单成功，返回奖品信息"],
        "businessAssertions": ["响应 code=200", "余额扣减正确"],
        "traceability": ["RISK-P0-001"],
        "data": {"productId": "225", "tableHint": "t_product_prize"},
    }
    base.update(extra)
    return base


def test_spec_task_oracle_is_structured_object_not_string(qa, tmp_path):
    write(
        tmp_path / "demo-backend" / "pom.xml",
        "<project><artifactId>demo-backend</artifactId></project>",
    )
    cases = _minimal_cases([_minimal_case()])
    result = qa.generate_spec_tasks_data(cases, repo=tmp_path)

    for task in result["tasks"]:
        for oracle_list in task["oracle"].values():
            for item in oracle_list:
                assert isinstance(item, dict), (
                    f"oracle item must be a dict, got {type(item).__name__}: {item!r}"
                )
                assert "assertion" in item, f"oracle item missing 'assertion': {item!r}"
                assert "type" in item, f"oracle item missing 'type': {item!r}"


def test_spec_task_assertions_sourced_from_business_assertions(qa, tmp_path):
    write(
        tmp_path / "demo-backend" / "pom.xml",
        "<project><artifactId>demo-backend</artifactId></project>",
    )
    case = _minimal_case(
        businessAssertions=["响应 code=200", "balance_change = totalDeducted"],
        expected=["下单成功"],
    )
    cases = _minimal_cases([case])
    result = qa.generate_spec_tasks_data(cases, repo=tmp_path)

    for task in result["tasks"]:
        flat = json.dumps(task["assertions"])
        assert "balance_change = totalDeducted" in flat, (
            f"businessAssertion not in task assertions: {task['assertions']}"
        )
        assert flat.count("balance_change = totalDeducted") == 1, (
            "businessAssertion duplicated in assertions"
        )


def test_spec_task_root_has_generation_metadata(qa, tmp_path):
    write(
        tmp_path / "demo-backend" / "pom.xml",
        "<project><artifactId>demo-backend</artifactId></project>",
    )
    cases = _minimal_cases([_minimal_case()])
    result = qa.generate_spec_tasks_data(cases, repo=tmp_path)

    assert "generationProfile" in result, "missing generationProfile"
    assert "minSpecsByPriority" in result, "missing minSpecsByPriority"
    assert "targetRatio" in result, "missing targetRatio"


def test_acceptance_mode_generates_api_task_plus_e2e_for_requires_e2e_risk(qa, tmp_path):
    write(
        tmp_path / "demo-backend" / "pom.xml",
        "<project><artifactId>demo-backend</artifactId></project>",
    )
    case = _minimal_case(requiresE2E=True)
    cases = _minimal_cases([case])
    result = qa.generate_spec_tasks_data(
        cases,
        repo=tmp_path,
        generation_profile="acceptance",
        min_specs_override="P0=1,P1=1,P2=1",
        ratio={"unit": 0, "integration": 0, "api": 1, "e2e": 0},
    )

    layers = [t["layer"] for t in result["tasks"]]
    assert "api" in layers, "acceptance mode must include an api task"
    assert "e2e" in layers, "requiresE2E=True must always produce at least one e2e task even in acceptance mode"


def test_spec_task_db_oracle_contains_table_hint_from_case_data(qa, tmp_path):
    write(
        tmp_path / "demo-backend" / "pom.xml",
        "<project><artifactId>demo-backend</artifactId></project>",
    )
    case = _minimal_case(data={"productId": "225", "tableHint": "t_product_prize"})
    cases = _minimal_cases([case])
    result = qa.generate_spec_tasks_data(cases, repo=tmp_path)

    db_assertions = []
    for task in result["tasks"]:
        db_assertions.extend(task["oracle"].get("db", []))

    flat = json.dumps(db_assertions)
    assert "t_product_prize" in flat or "225" in flat, (
        f"case data (tableHint/productId) not reflected in DB oracle: {db_assertions}"
    )


def test_oracle_mapping_gate_fails_when_p0_risk_not_covered(qa, tmp_path):
    risk_data = {
        "risks": [
            {
                "id": "RISK-P0-001",
                "priority": "P0",
                "category": "money-reward-settlement",
                "requiredAssertions": ["余额扣减正确"],
                "requiresE2E": False,
            }
        ]
    }
    spec_tasks = {
        "tasks": [
            {
                "id": "SPEC-TC-P0-001-API-001",
                "sourceCaseId": "TC-P0-001",
                "assertions": ["code=200"],
                "oracle": {"api": [{"type": "api", "assertion": "code=200"}], "db": [], "ui": [], "sideEffects": [], "negativeAssertions": []},
                "traceability": [],
            }
        ]
    }

    result = qa.assert_oracle_mapping_data(risk_data, spec_tasks)

    assert result["status"] == "failed", f"expected failed, got: {result['status']}"
    finding_ids = [f.get("riskId") for f in result.get("findings", [])]
    assert "RISK-P0-001" in finding_ids


def test_oracle_mapping_gate_passes_when_all_p0_p1_risks_mapped(qa, tmp_path):
    risk_data = {
        "risks": [
            {
                "id": "RISK-P0-001",
                "priority": "P0",
                "category": "money-reward-settlement",
                "requiredAssertions": ["余额扣减正确"],
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
                "oracle": {"api": [], "db": [{"type": "db", "assertion": "余额扣减正确", "sourceRiskId": "RISK-P0-001"}], "ui": [], "sideEffects": [], "negativeAssertions": []},
                "traceability": ["RISK-P0-001"],
            }
        ]
    }

    result = qa.assert_oracle_mapping_data(risk_data, spec_tasks)

    assert result["status"] == "passed", f"expected passed, got: {result['status']}\nfindings: {result.get('findings')}"
