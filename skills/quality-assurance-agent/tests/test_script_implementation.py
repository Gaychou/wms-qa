"""测试脚本实现真实性：映射到文件 ≠ 实现了测试。"""
from __future__ import annotations

from pathlib import Path


def _spec_tasks(target_files):
    """构造 N 个 task 映射到同一个 targetFile。"""
    tasks = []
    for i, tf in enumerate(target_files):
        for _ in range(3):  # 每个文件映射 3 个 task
            tasks.append({
                "id": f"SPEC-{i}-{_}-API-001",
                "sourceCaseId": f"TC-P0-{i:03d}",
                "targetFile": tf,
                "layer": "api",
            })
    return {"tasks": tasks}


def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_target_file_missing_is_not_implemented(qa, tmp_path):
    spec = _spec_tasks(["src/test/java/qa/OpenBoxTest.java"])
    result = qa.assert_script_implementation_data(spec, tmp_path)
    assert result["status"] == "failed"
    types = [f["type"] for f in result["findings"]]
    assert "target-file-missing" in types


def test_placeholder_stub_is_not_implemented(qa, tmp_path):
    stub = tmp_path / "tests" / "api" / "tc.sh"
    _write(stub, '#!/bin/bash\necho "BLOCKED: ..."\nexit 0\n')
    spec = _spec_tasks(["tests/api/tc.sh"])
    result = qa.assert_script_implementation_data(spec, tmp_path)
    types = [f["type"] for f in result["findings"]]
    assert "placeholder-stub" in types


def test_test_method_count_less_than_task_count_fails(qa, tmp_path):
    """54 个 task 映射到只有 7 个 @Test 的文件 → 映射未实现。"""
    java = tmp_path / "src/test/java/qa/OpenBoxTest.java"
    _write(java, "class OpenBoxTest {\n  @Test void t1() {}\n  @Test void t2() {}\n}\n")  # 2 个 @Test
    spec = {"tasks": []}
    for i in range(5):  # 5 个 task 映射到这个文件
        spec["tasks"].append({"id": f"S-{i}", "sourceCaseId": f"C-{i}", "targetFile": "src/test/java/qa/OpenBoxTest.java", "layer": "unit"})
    result = qa.assert_script_implementation_data(spec, tmp_path)
    types = [f["type"] for f in result["findings"]]
    assert "mapping-not-implemented" in types


def test_test_method_count_sufficient_passes(qa, tmp_path):
    java = tmp_path / "src/test/java/qa/OpenBoxTest.java"
    _write(java, "class OpenBoxTest {\n  @Test void t1() {}\n  @Test void t2() {}\n  @Test void t3() {}\n}\n")  # 3 个 @Test
    spec = {"tasks": []}
    for i in range(3):  # 3 个 task，方法数 >= task 数
        spec["tasks"].append({"id": f"S-{i}", "sourceCaseId": f"C-{i}", "targetFile": "src/test/java/qa/OpenBoxTest.java", "layer": "unit"})
    result = qa.assert_script_implementation_data(spec, tmp_path)
    assert result["status"] == "passed"
