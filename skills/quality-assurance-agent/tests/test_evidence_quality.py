"""测试证据质量硬门禁：passed 禁止手动验证，blocked 必须带侦察证据。"""
from __future__ import annotations


def test_passed_evidence_rejects_manual_verify(qa):
    """passed 的 evidence 含「手动验证」→ 判无效（不能靠手工核对冒充真实执行）。"""
    assert qa.has_meaningful_evidence({"evidence": ["手动验证通过"]}) is False
    assert qa.has_meaningful_evidence({"evidence": ["手动 MCP 核对 asset_status=1"]}) is False


def test_passed_evidence_accepts_real_output(qa):
    assert qa.has_meaningful_evidence({"evidence": ["PASS [code]: 200"]}) is True
    assert qa.has_meaningful_evidence({"evidence": ["exit_code: 0"]}) is True


def test_blocked_data_reason_requires_recon_evidence(qa):
    """数据类 blocked（「需数据/账号/资产」）但无侦察证据 → 判无效。"""
    task = {
        "blocker": "需封禁账号才能测试",
        "nextAction": "补充数据",
        "owner": "qa",
        "notes": "待补充数据",
    }
    assert qa.has_blocker_evidence(task) is False, "数据阻塞无 SELECT 侦察证据必须判无效"


def test_blocked_data_reason_with_recon_passes(qa):
    task = {
        "blocker": "需封禁账号，已 SELECT 侦察：count(*)=0 无可用账号",
        "nextAction": "补充数据",
        "owner": "qa",
        "notes": "已侦察",
    }
    assert qa.has_blocker_evidence(task) is True


def test_blocked_env_reason_no_recon_needed(qa):
    """环境类 blocked（服务不可达）不需要数据侦察证据。"""
    task = {
        "blocker": "后端服务不可达",
        "nextAction": "启动服务",
        "owner": "qa",
        "notes": "待启动",
    }
    assert qa.has_blocker_evidence(task) is True
