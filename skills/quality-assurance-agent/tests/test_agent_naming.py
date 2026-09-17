#!/usr/bin/env python3
"""回归测试：agent 取值的规范名与 Playwright 词表的翻译。

本 CLI 的 agent 规范名是 `claude-code`（与 npx skills 等生态工具一致），
但下游 Playwright 的 `init-agents --loop` 用的是**另一套**词表
（claude / codex / copilot / opencode / vscode / vscode-legacy）。
两套名字直接对接会被 npx 拒绝：

    option '--loop <loop>' argument 'claude-code' is invalid.
    Allowed choices are claude, codex, copilot, opencode, vscode, vscode-legacy.

所以规范名只在本 CLI 边界内使用，调用 Playwright 前必须翻译回去。
这两个函数就是那条边界，钉住它们。

历史名 `claude` 保留为别名：`QA_AGENT=claude` 已经写进既有项目的
.qa-agent/local/.env，直接改名会让那些项目静默失效。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import (
    AGENT_BOTH,
    AGENT_CHOICES,
    AGENT_CLAUDE,
    AGENT_CODEX,
    normalize_agent_name,
    playwright_loop_name,
)


# ── 规范名 ──────────────────────────────────────────────────────────────

def test_canonical_name_is_claude_code():
    assert AGENT_CLAUDE == "claude-code"
    assert "claude-code" in AGENT_CHOICES
    assert "claude" not in AGENT_CHOICES, "旧名不应作为规范取值出现在 choices 里"


def test_legacy_name_normalizes():
    assert normalize_agent_name("claude") == "claude-code", (
        "旧名 claude 未归一——既有项目 .env 里的 QA_AGENT=claude 会失效"
    )
    assert normalize_agent_name("CLAUDE") == "claude-code", "应大小写不敏感"
    assert normalize_agent_name("  claude  ") == "claude-code", "应容忍空白"


def test_canonical_and_others_pass_through():
    assert normalize_agent_name("claude-code") == "claude-code"
    assert normalize_agent_name("codex") == "codex"
    assert normalize_agent_name("both") == "both"
    assert normalize_agent_name("") == ""
    assert normalize_agent_name(None) == ""


def test_unknown_value_unchanged():
    """不认识的值原样返回，交由调用方的 choices 去拒绝。"""
    assert normalize_agent_name("copilot") == "copilot"
    assert normalize_agent_name("whatever") == "whatever"


# ── Playwright 词表翻译 ────────────────────────────────────────────────

def test_playwright_translation():
    assert playwright_loop_name("claude-code") == "claude", (
        "未翻译成 Playwright 的词表——npx playwright init-agents 会拒绝 claude-code"
    )
    assert playwright_loop_name("claude") == "claude", "旧名同样要翻译正确"
    assert playwright_loop_name("codex") == "codex"


def test_playwright_passthrough_for_other_loops():
    """Playwright 还支持 copilot / opencode / vscode，不能被本 CLI 的映射吃掉。"""
    for name in ("copilot", "opencode", "vscode", "vscode-legacy"):
        assert playwright_loop_name(name) == name
