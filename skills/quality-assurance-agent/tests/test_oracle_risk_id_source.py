#!/usr/bin/env python3
"""回归测试：spec task 的风险关联必须来自用例声明的风险 id。

历史缺陷（门禁误报，逼人补不存在的覆盖）：

  `oracle_for_spec_task()` 曾这样取风险号：

      traceability = case.get("traceability") or []
      source_risk_id = traceability[0] if traceability else ""

  而 `test-cases.json` 的 `traceability` 按 schema（references/test-case-schema.md）
  是混合内容——requirement id / issue id / 代码路径 / API 路径都允许。使用者照
  schema 写 API 路径时，oracle 各项的 `sourceRiskId` 就被写成
  `"POST /open-box/open-by-usd"`，于是：

      Oracle mapping gate FAILED: 6 P0/P1 risks not covered

  而用例到风险的映射其实是对的。使用者会据此去补并不存在的覆盖。

  这与 `project_risk_coverage` 的误读是同一个根因（同名字段在两个 schema 里语义
  不同），只是出口不同——本文件守的这一个出口叫 oracle。

修复：取 `_case_risk_ids(case)`（显式 riskIds 为主，兼容旧数据里形态正确的
traceability 条目）；同时让 `build_spec_task` 把用例的全部风险 id 写进 task 级
`traceability`——生成器 SKILL.md 本就把该字段定义为「关联的 risk ID 列表」，
而代码此前从不写它，多风险用例只能靠 oracle 那一个字段兜着。
"""

from __future__ import annotations

API_PATH = "POST /open-box/open-by-usd"


def _case(**extra):
    case = {
        "id": "TC-P0-001",
        "priority": "P0",
        "title": "USD 开盒扣款",
        "businessAssertions": ["接口返回 code=200", "数据库余额扣减与商品单价一致"],
    }
    case.update(extra)
    return case


def _source_risk_ids(oracle):
    ids = set()
    for items in oracle.values():
        for item in items:
            if item.get("sourceRiskId"):
                ids.add(str(item["sourceRiskId"]))
    return ids


def test_source_risk_id_comes_from_risk_ids(qa):
    """用例把 API 路径写在 traceability、风险号写在 riskIds → 取风险号。"""
    oracle = qa.oracle_for_spec_task(_case(riskIds=["RISK-P0-001"], traceability=[API_PATH]), "api", "main")

    assert _source_risk_ids(oracle) == {"RISK-P0-001"}


def test_api_path_is_never_used_as_a_risk_id(qa):
    """没有风险关联时，宁可留空，也不能把 API 路径当风险号。"""
    oracle = qa.oracle_for_spec_task(_case(traceability=[API_PATH]), "api", "main")

    assert API_PATH not in _source_risk_ids(oracle), f"API 路径被当成风险号：{_source_risk_ids(oracle)}"
    assert _source_risk_ids(oracle) == set()


def test_legacy_traceability_risk_id_still_works(qa):
    """兼容旧数据：风险号写在 traceability 里且形态正确，仍然认。"""
    oracle = qa.oracle_for_spec_task(_case(traceability=["RISK-P1-002"]), "api", "main")

    assert _source_risk_ids(oracle) == {"RISK-P1-002"}


def _maven_repo(tmp_path):
    """build_spec_task 需要能从 repo 识别项目类型（pom.xml / package.json）。"""
    (tmp_path / "pom.xml").write_text(
        "<project><modelVersion>4.0.0</modelVersion><groupId>g</groupId>"
        "<artifactId>a</artifactId><version>1</version></project>",
        encoding="utf-8",
    )
    return tmp_path


def test_spec_task_carries_all_case_risk_ids(qa, tmp_path):
    """task 级 traceability 要带上用例的全部风险 id（多风险用例靠它补全）。"""
    case = _case(riskIds=["RISK-P0-001", "RISK-P1-003"])
    focus = {"kind": "main", "title": "主成功路径", "assertion": "接口返回 code=200"}

    task = qa.build_spec_task(case, "api", focus, 1, _maven_repo(tmp_path))

    assert task["traceability"] == ["RISK-P0-001", "RISK-P1-003"]


def test_gate_reads_risk_ids_from_generated_task(qa, tmp_path):
    """端到端：生成器产出的 task，门禁的风险读取器必须能取到风险号。"""
    case = _case(riskIds=["RISK-P0-001"])
    focus = {"kind": "main", "title": "主成功路径", "assertion": "接口返回 code=200"}

    task = qa.build_spec_task(case, "api", focus, 1, _maven_repo(tmp_path))

    assert "RISK-P0-001" in qa._task_risk_ids(task), "门禁读不到风险号，就会误报未覆盖"
