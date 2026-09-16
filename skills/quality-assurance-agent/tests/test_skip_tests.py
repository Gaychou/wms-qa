"""测试 skipTests=true 的应对：命令绕过 + surefire 检测假通过。"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


def test_maven_command_overrides_skip_tests(qa):
    """maven 测试命令必须显式 -DskipTests=false，覆盖 pom.xml 的 skipTests=true。"""
    cmd = qa.command_for_spec_task("unit", "svc", "svc/src/test/java/qa/OpenBoxTest.java", "maven")
    assert "-DskipTests=false" in cmd
    assert "-Dmaven.test.skip=false" in cmd

    cmd_api = qa.command_for_spec_task("api", "svc", "svc/src/test/java/qa/OpenBoxApiTest.java", "maven")
    assert "-DskipTests=false" in cmd_api


def test_surefire_zero_tests_not_passed(qa, tmp_path):
    """skipTests 生成 0 tests 报告时，parse_surefire_reports 不得判为 passed。"""
    reports = tmp_path / "surefire"
    reports.mkdir()
    # 模拟 skipTests 后的空报告（tests=0）
    xml = ET.Element("testsuite", {"name": "OpenBoxTest", "tests": "0", "failures": "0", "errors": "0", "skipped": "0"})
    ET.ElementTree(xml).write(reports / "TEST-OpenBoxTest.xml", encoding="utf-8")

    summary = qa.parse_surefire_reports(reports)

    assert summary["status"] != "passed", "0 tests 的 surefire 报告不得判 passed"
    assert summary["tests"] == 0


def test_surefire_real_tests_passed(qa, tmp_path):
    reports = tmp_path / "surefire"
    reports.mkdir()
    xml = ET.Element("testsuite", {"name": "OpenBoxTest", "tests": "54", "failures": "0", "errors": "0", "skipped": "0"})
    ET.ElementTree(xml).write(reports / "TEST-OpenBoxTest.xml", encoding="utf-8")

    summary = qa.parse_surefire_reports(reports)
    assert summary["status"] == "passed"
    assert summary["tests"] == 54
