#!/usr/bin/env python3
"""回归测试：completion 门禁必须把「业务没验证」和「计划没建完」分开。

历史缺陷（正确输入被判 failed）：

  `generate-spec-tasks` 按测试金字塔给每条用例自动展开 8 个 task。使用者把 17 条
  业务用例全部执行通过（case-not-verified 已清零）后，门禁仍然 failed——原因是
  另外 76 个自动展开的 task 没实现。

  于是使用者两难：要么为凑数补大量低信息量测试，要么承受「未完成」判定。实际发生
  的是前者（补了 52 个单测/集成测试），原话是「为了迁就门禁的粒度，而不是因为业务
  风险」。一个判据错位的门禁会教使用者绕过它——本次流程中使用者自述「差点伪造
  task 状态来过门禁」。

  本工具确实要求测试金字塔（SKILL.md 明写「验收同样要有单元测试」），但那属于
  **计划完成度**，该由 coverage-balance 管；completion 该断言的是「这轮跑完了、
  业务验证了没有」。两件事混成一个 fail，就是上面那个后果。

修复：task-not-implemented 降为 warn（只报告不阻断），阻断交给用例层的
case-not-verified。未实现的 task 不再重复记一条 task-not-executed。

注意 `case-under-min-spec-tasks` 不在本次修复范围：它数的是**声明**的 task 数
（含未实现），衡量「计划铺得够不够」，与「实现没实现」是两回事，行为不变。
"""

from __future__ import annotations

# P0 用例的默认最小 task 数（DEFAULT_SPEC_TASK_MIN_BY_PRIORITY）
P0_MIN_TASKS = 8


def _cases():
    return {
        "version": "1.0",
        "cases": [
            {"id": "TC-P0-001", "priority": "P0", "title": "用例", "module": "order",
             "type": "business", "layer": "api", "automation": "automated", "status": "confirmed"},
        ],
    }


def _task(index, impl="not-implemented", exec_status="not-run", evidence=None):
    return {
        "id": f"SPEC-TC-P0-001-{index:03d}",
        "sourceCaseId": "TC-P0-001",
        "priority": "P0",
        "layer": "unit" if index > 1 else "api",
        "targetFile": f"tests/case-{index}.sh",
        "testName": "用例测试",
        "command": "bash test.sh",
        "assertions": ["code=200"],
        "implementationStatus": impl,
        "executionStatus": exec_status,
        "evidence": evidence if evidence is not None else [],
    }


def _plan(*overrides):
    """铺满 P0 下限 8 个 task；overrides 按索引覆盖，其余默认「未实现」。"""
    tasks = [_task(i) for i in range(1, P0_MIN_TASKS + 1)]
    for index, kwargs in overrides:
        tasks[index - 1] = _task(index, **kwargs)
    return {"tasks": tasks}


def _types(result):
    return [f["type"] for f in result["findings"]]


def _severity_of(result, type_):
    return {f["type"]: f["severity"] for f in result["findings"]}.get(type_)


def _verified_plus_backlog():
    """本次事故的真实形状：1 个 task 真实通过，其余 7 个展开 task 未实现。"""
    return _plan((1, {"impl": "implemented", "exec_status": "passed", "evidence": ["PASS [code]: 200"]}))


def test_unimplemented_sibling_tasks_do_not_block_verified_case(qa):
    """核心场景：业务已通过，同期未实现的展开 task 不得把门禁判 failed。"""
    result = qa.assert_completion_data(_cases(), _verified_plus_backlog())

    assert "case-not-verified" not in _types(result), "有 passed task，用例已验证"
    assert "case-under-min-spec-tasks" not in _types(result), "前提：已铺满 P0 下限"
    assert result["status"] == "passed", f"业务已验证，不该被计划完成度判失败：{_types(result)}"


def test_unimplemented_is_warn_not_fail(qa):
    """计划完成度仍需被报告出来，只是不再阻断。"""
    result = qa.assert_completion_data(_cases(), _verified_plus_backlog())

    assert "task-not-implemented" in _types(result), "完成度信息不能丢"
    assert _severity_of(result, "task-not-implemented") == "warn"


def test_unimplemented_task_is_not_also_reported_as_unexecuted(qa):
    """没实现的 task 谈不上「没执行」，不重复记一条账。"""
    result = qa.assert_completion_data(_cases(), _verified_plus_backlog())

    assert "task-not-executed" not in _types(result), f"重复记账：{_types(result)}"


def test_counters_still_report_incompleteness(qa):
    """降级为 warn 不等于隐藏——计数必须照常反映未实现数量。"""
    result = qa.assert_completion_data(_cases(), _verified_plus_backlog())

    assert result["summary"]["unimplemented"] == P0_MIN_TASKS - 1


def test_case_not_verified_still_blocks(qa):
    """真正的阻断依据必须保留：用例一条都没执行通过 = 业务未验证 → failed。"""
    result = qa.assert_completion_data(_cases(), _plan())

    assert "case-not-verified" in _types(result)
    assert result["status"] == "failed"


def test_implemented_but_unexecuted_still_blocks(qa):
    """已实现却没执行的 task 仍是真缺口——测试写了没跑，与「没写」不同。"""
    result = qa.assert_completion_data(
        _cases(),
        _plan(
            (1, {"impl": "implemented", "exec_status": "passed", "evidence": ["PASS [code]: 200"]}),
            (2, {"impl": "implemented", "exec_status": "not-run", "evidence": []}),
        ),
    )

    assert "task-not-executed" in _types(result)
    assert _severity_of(result, "task-not-executed") == "fail"
    assert result["status"] == "failed"


def test_under_min_spec_tasks_still_blocks(qa):
    """计划铺得不够（声明数低于下限）仍阻断——本次未改动该行为。"""
    result = qa.assert_completion_data(
        _cases(),
        {"tasks": [_task(1, impl="implemented", exec_status="passed", evidence=["PASS [code]: 200"])]},
    )

    assert "case-under-min-spec-tasks" in _types(result)
    assert result["status"] == "failed"
