#!/usr/bin/env python3
"""回归测试：P2 一组的可用性修复。

四处历史缺陷，都来自同一份外部使用反馈：

  ① `render-report` 的归档副本功能没接出来。实现里写着「指定 --module 和 --run-type 时
     额外输出归档副本」，取的是 `getattr(args, "module")`——而这两个参数从未注册进
     argparse，永远取到 None。文档没写错（SKILL.md 确实写了用法），是参数漏了，
     使用者只能自己 cp。

  ② 就绪判定词汇混排。每条 finding 各盖一个 decision 章（Incomplete / Not Ready 混着
     出现），要确定最终落哪一档还得回头查文档。findings 应当只描述事实，档位由一个
     顶层字段给出。

  ③ `manifest` 只 dump 原始 JSON，只列路径不判断是否存在——`.qa-agent/current/` 下
     二十来个 json，缺的正是「哪个产物真落盘了」的总览。

  ④ 服务「可达」不等于它依赖的中间件版本支持所需能力。使用者实测：test 环境 Redis
     4.0.8，而项目用 Redis Streams 做埋点（需 ≥ 5.0）——服务照常启动，doctor 一路绿灯，
     埋点链路整体不可信却无人察觉。
"""

from __future__ import annotations

import argparse
import json


# --- ① render-report 的归档参数 ---


def test_render_report_accepts_module_and_run_type(qa):
    """参数必须真的注册了——之前是 unrecognized arguments，归档副本永远不生成。"""
    args = qa.build_parser().parse_args(
        ["render-report", "--module", "open-box", "--run-type", "acceptance"]
    )

    assert args.module == "open-box"
    assert args.run_type == "acceptance"


# --- ② 就绪判定词汇统一 ---


def _readiness(qa, **overrides):
    kwargs = {
        "completion_data": {"status": "passed", "decision": "complete"},
        "code_review_data": {"status": "passed", "summary": {"findings": 0, "blockingFindings": 0}, "findings": []},
        "report_freshness_data": {"status": "passed"},
        "evidence_integrity_data": {"status": "passed", "findings": []},
    }
    kwargs.update(overrides)
    return qa.assert_readiness_data(**kwargs)


def test_findings_do_not_carry_their_own_verdict(qa):
    """findings 只描述事实；档位由顶层 decision 一个字段给出。"""
    result = _readiness(qa, completion_data={})

    assert result["findings"], "前提：这里应当有 finding"
    for finding in result["findings"]:
        assert "decision" not in finding, f"finding 又盖了自己的档位章：{finding}"


def test_missing_artifact_yields_incomplete(qa):
    """缺产物 = 流程没走完 → Incomplete。"""
    result = _readiness(qa, completion_data={})

    assert result["decision"] == "Incomplete"


def test_blocking_code_review_yields_not_ready(qa):
    """代码审查有 blocking finding = 走完了但不达标 → Not Ready。"""
    result = _readiness(
        qa,
        code_review_data={
            "status": "failed",
            "summary": {"findings": 1, "blockingFindings": 1},
            "findings": [{"type": "blocking-code-review-finding", "severity": "fail"}],
        },
    )

    assert result["decision"] == "Not Ready"


def test_clean_run_is_ready(qa):
    assert _readiness(qa)["decision"] == "Ready"


# --- ③ manifest 总览 ---


def _manifest_repo(tmp_path):
    current = tmp_path / ".qa-agent" / "current"
    current.mkdir(parents=True, exist_ok=True)
    (current / "present.json").write_text("{}", encoding="utf-8")
    (current / "manifest.json").write_text(json.dumps({
        "version": "1.0",
        "currentStage": "risk-analyzer",
        "artifacts": {
            "present": ".qa-agent/current/present.json",
            "gone": ".qa-agent/current/gone.json",
        },
        "status": {"risksAnalyzed": "done"},
    }), encoding="utf-8")
    return tmp_path


def test_manifest_brief_marks_present_and_missing(qa, tmp_path, capsys):
    qa.cmd_manifest(argparse.Namespace(repo=str(_manifest_repo(tmp_path)), brief=True))

    out = capsys.readouterr().out
    assert "risk-analyzer" in out
    assert "✓ present" in out, f"落盘的产物要打勾：{out}"
    assert "✗ gone" in out, f"没落盘的产物要打叉：{out}"


def test_manifest_default_still_dumps_json(qa, tmp_path, capsys):
    """不加 --brief 时保持原样，供程序消费。"""
    qa.cmd_manifest(argparse.Namespace(repo=str(_manifest_repo(tmp_path)), brief=False))

    out = capsys.readouterr().out
    assert json.loads(out)["currentStage"] == "risk-analyzer"


# --- ④ 中间件能力不匹配 ---


def _service_log(tmp_path, name, text):
    current = tmp_path / ".qa-agent" / "current"
    current.mkdir(parents=True, exist_ok=True)
    (current / f"{name}.out.log").write_text(text, encoding="utf-8")


def test_capability_scan_detects_the_reported_case(qa, tmp_path):
    """使用者实测的那一条：Redis 4.0.8 不认识 XREADGROUP。"""
    _service_log(tmp_path, "api",
                 "2026-09-18 ERROR RedisStreamTrackConsumer 读取Stream失败\n"
                 "  redis.clients.jedis.exceptions.JedisDataException: ERR unknown command 'XREADGROUP'\n")

    hits = qa.scan_service_logs_for_capability_errors(tmp_path, ["api"])

    assert "api" in hits
    assert any("XREADGROUP" in line for line in hits["api"])


def test_capability_scan_silent_on_clean_log(qa, tmp_path):
    _service_log(tmp_path, "api", "2026-09-18 INFO Started Application in 8.2 seconds\n")

    assert qa.scan_service_logs_for_capability_errors(tmp_path, ["api"]) == {}


def test_capability_scan_ignores_absent_log(qa, tmp_path):
    assert qa.scan_service_logs_for_capability_errors(tmp_path, ["never-ran"]) == {}
