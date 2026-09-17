#!/usr/bin/env python3
"""回归测试：spec task 的 methodName 契约，以及按方法名校验的实现门禁。

背景：task.testName 是中文业务描述（「单次下单正确扣减余额 - 正常路径」），
而代码里是 deductBalanceAndWriteLog。两者对不上，于是「把任务映射到某个文件」
可以被冒充成「实现了测试」——只要文件里凑够数量的 @Test 就能过。

修法：生成阶段把可执行的方法名定死（methodName），执行阶段按名字逐个核对。
数量校验只能保证「够数」，保证不了「对得上」。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import (
    assert_script_implementation_data,
    discover_test_method_names,
    method_name_for_task_id,
)


def _java(methods) -> str:
    body = "\n".join(
        f"    @DisplayName(\"用例 {m}\")\n    @Test\n    void {m}() {{ }}\n"
        for m in methods
    )
    return f"package qa;\n\npublic class OpenBoxTest {{\n{body}}}\n"


def _task(file_rel: str, method: str = "", task_id: str = "SPEC-TC-P0-001-UNIT-001") -> dict:
    task = {"id": task_id, "targetFile": file_rel, "testName": "中文业务描述 - 正常路径"}
    if method:
        task["methodName"] = method
    return task


# ── 方法名派生 ──────────────────────────────────────────────────────────

def test_method_name_is_valid_identifier():
    name = method_name_for_task_id("SPEC-TC-P0-001-UNIT-001")

    assert name == "specTcP0001Unit001"
    assert name[:1].isalpha(), "方法名不能以数字开头"
    assert name.isidentifier(), f"{name!r} 不是合法标识符"


def test_method_name_handles_edge_input():
    assert method_name_for_task_id("") == "specTask"
    assert method_name_for_task_id("---") == "specTask"
    assert method_name_for_task_id("001-x").isidentifier()


# ── 方法名提取 ──────────────────────────────────────────────────────────

def test_discover_java_test_methods(tmp_path):
    f = tmp_path / "OpenBoxTest.java"
    f.write_text(_java(["alpha", "beta", "gamma"]), encoding="utf-8")

    assert discover_test_method_names(f) == {"alpha", "beta", "gamma"}


def test_discover_returns_none_for_non_java(tmp_path):
    """非 Java（如 Playwright spec）无法按名字核对，返回 None 表示只能按数量校验。"""
    f = tmp_path / "tc-p1-007.spec.ts"
    f.write_text("test('TC-P1-007 ...', async ({page}) => {});\n", encoding="utf-8")

    assert discover_test_method_names(f) is None


# ── 门禁：按名字核对 ────────────────────────────────────────────────────

def test_declared_method_missing_is_flagged(tmp_path):
    """数量对得上，但方法名对不上 —— 这正是数量校验抓不住的情形。"""
    (tmp_path / "OpenBoxTest.java").write_text(_java(["alpha", "beta"]), encoding="utf-8")
    tasks = {
        "tasks": [
            _task("OpenBoxTest.java", "specTcP0001Unit001"),
            _task("OpenBoxTest.java", "specTcP0001Unit002", "SPEC-TC-P0-001-UNIT-002"),
        ]
    }

    result = assert_script_implementation_data(tasks, tmp_path)

    assert result["status"] == "failed"
    finding = next(f for f in result["findings"] if f["type"] == "method-not-implemented")
    assert finding["missingMethodCount"] == 2, "方法数相等，但声明的方法一个都不存在"
    assert set(finding["missingMethods"]) == {"specTcP0001Unit001", "specTcP0001Unit002"}


def test_all_declared_methods_present_passes(tmp_path):
    (tmp_path / "OpenBoxTest.java").write_text(
        _java(["specTcP0001Unit001", "specTcP0001Unit002"]), encoding="utf-8"
    )
    tasks = {
        "tasks": [
            _task("OpenBoxTest.java", "specTcP0001Unit001"),
            _task("OpenBoxTest.java", "specTcP0001Unit002", "SPEC-TC-P0-001-UNIT-002"),
        ]
    }

    result = assert_script_implementation_data(tasks, tmp_path)

    assert result["status"] == "passed", f"方法都在却判失败：{result['findings']}"


def test_falls_back_to_count_without_method_name(tmp_path):
    """旧产物没有 methodName —— 退回按数量校验，保持兼容。"""
    (tmp_path / "OpenBoxTest.java").write_text(_java(["alpha"]), encoding="utf-8")
    tasks = {"tasks": [_task("OpenBoxTest.java"), _task("OpenBoxTest.java", "", "SPEC-TC-P0-001-UNIT-002")]}

    result = assert_script_implementation_data(tasks, tmp_path)

    assert result["status"] == "failed"
    assert any(f["type"] == "mapping-not-implemented" for f in result["findings"])


def test_non_java_target_uses_count_check(tmp_path):
    """Playwright spec 无法按名字核对，仍走数量校验（且不能被误判为通过）。"""
    (tmp_path / "tc-p1-007.spec.ts").write_text(
        "test('a', async ({page}) => {});\ntest('b', async ({page}) => {});\n", encoding="utf-8"
    )
    tasks = {"tasks": [_task("tc-p1-007.spec.ts", "specTcP1007E2E001")]}

    result = assert_script_implementation_data(tasks, tmp_path)

    # 一个 task 对一个非占位 spec：数量校验通过
    assert result["status"] == "passed"
