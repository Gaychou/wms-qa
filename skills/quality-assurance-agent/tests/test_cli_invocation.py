#!/usr/bin/env python3
"""回归测试：工具输出的命令必须是用户能直接跑通的那一种。

文档和工具输出里一律写 `ming-qa <cmd>`，但那要求 skill 的 bin/ 已经在 PATH 上。
用 npx skills 或插件市场安装的用户没做过这一步——而 init-project 的「下一步」
正是他们安装完之后看到的第一串命令，照抄会得到 `ming-qa: command not found`。

所以 cli_invocation() 会实际探测一次 PATH：有 ming-qa 就沿用，没有就回退成本脚本的
真实路径。这里钉住两个分支，避免以后有人图省事又写死成 "ming-qa"。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import qa_agent
from qa_agent import cli_invocation


@pytest.fixture(autouse=True)
def _clear_env_override(monkeypatch):
    monkeypatch.delenv("QA_AGENT_CLI", raising=False)


def test_uses_ming_qa_when_it_is_on_path(monkeypatch):
    monkeypatch.setattr(qa_agent.shutil, "which", lambda name: "/usr/bin/ming-qa")

    assert cli_invocation() == "ming-qa"


def test_falls_back_to_script_path_when_absent(monkeypatch):
    """PATH 上没有 ming-qa（npx skills / 插件市场安装的默认状态）时，
    必须回退到本脚本的真实路径，否则用户拿到的是一条跑不通的命令。"""
    monkeypatch.setattr(qa_agent.shutil, "which", lambda name: None)

    got = cli_invocation()

    assert got != "ming-qa", "PATH 上没有 ming-qa 却仍然输出 ming-qa —— 用户照抄会 command not found"
    assert "qa_agent.py" in got, f"回退命令里应含本脚本路径，实际：{got!r}"
    assert got.startswith("python"), f"回退命令应以 python 开头，实际：{got!r}"


def test_qa_agent_cli_override_wins(monkeypatch):
    """显式设了 QA_AGENT_CLI 就按用户的意思来（文档里的解析优先级第一条）。"""
    monkeypatch.setenv("QA_AGENT_CLI", "/custom/path/ming-qa")
    monkeypatch.setattr(qa_agent.shutil, "which", lambda name: None)

    assert cli_invocation() == "ming-qa"
