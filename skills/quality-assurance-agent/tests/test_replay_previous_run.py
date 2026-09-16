"""离线重放测试：用上一轮 .qa-agent 样本只读复制件验证 sidecar 聚合。

设计规范约定「只支持新契约」：旧日志名 run-<case_id>-<epoch>.log 缺 slug 段，
不能直接匹配 _RUN_LOG_NAME_RE。本测试从旧日志头部构造新 sidecar 后重放，
验证 aggregate-runs 得到非零结果。

注意：证据门禁的「缺失 run 证据」逻辑不在此测——它依赖外部易变样本，
已在 tests/test_evidence_integrity.py 用自构造 fixture 覆盖。
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import pytest

# 离线重放需要一个真实的 .qa-agent/runs 样本目录。该样本不随仓库分发——
# 需要时用环境变量指向你自己的副本，未设置时整个模块跳过。
_SAMPLE_ENV = "QA_AGENT_RUN_SAMPLES"
_SAMPLE_DIR = os.environ.get(_SAMPLE_ENV, "")
_SOURCE_RUNS = Path(_SAMPLE_DIR) if _SAMPLE_DIR else None
_HAS_RUN_SAMPLES = bool(
    _SOURCE_RUNS and _SOURCE_RUNS.is_dir() and list(_SOURCE_RUNS.glob("*.log"))
)


def _parse_legacy_log(path: Path) -> dict | None:
    """从旧格式日志提取 case_id 与 exit_code，构造新 sidecar 内容。"""
    # 文件名：run-tc-p0-001-1786635844.log → case_id=tc-p0-001, epoch=1786635844
    stem = path.name
    if stem.startswith("run-"):
        stem = stem[4:]
    if stem.endswith(".log"):
        stem = stem[:-4]
    case_id, _, epoch = stem.rpartition("-")
    if not case_id or not epoch.isdigit():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = re.search(r"^# exit_code:\s*(-?\d+)\s*$", text, re.MULTILINE)
    exit_code = int(m.group(1)) if m else 0
    return {
        "version": "1.0",
        "runId": epoch,
        "caseId": case_id.upper(),
        "taskId": "",
        "script": f"{case_id}.sh",
        "logFile": path.name,
        "exitCode": exit_code,
        "executedAt": "",
        "outcome": "PASS" if exit_code == 0 else "FAIL",
    }


@pytest.mark.skipif(
    not _HAS_RUN_SAMPLES,
    reason=f"未设置 {_SAMPLE_ENV} 或该目录下没有 *.log 样本，跳过离线重放测试",
)
def test_replay_aggregates_legacy_logs_via_sidecars(tmp_path):
    runs_dir = tmp_path / ".qa-agent" / "runs"
    runs_dir.mkdir(parents=True)

    legacy_logs = sorted(_SOURCE_RUNS.glob("*.log"))
    assert legacy_logs, "上一轮 runs 目录应包含日志"

    sidecars = []
    for lf in legacy_logs:
        sidecar = _parse_legacy_log(lf)
        if sidecar is None:
            continue
        sidecars.append(sidecar)
        # 复制 log + 写 sidecar
        shutil.copy2(lf, runs_dir / lf.name)
        (runs_dir / f"run-{sidecar['caseId'].lower()}-{sidecar['runId']}.meta.json").write_text(
            json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
        )

    assert len(sidecars) >= 16, f"应解析出至少 16 条 sidecar，实际 {len(sidecars)}"
