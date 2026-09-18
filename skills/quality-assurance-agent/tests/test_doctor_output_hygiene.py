#!/usr/bin/env python3
"""回归测试：工具输出里的「下一步」必须是能直接跑通的命令。

历史缺陷：doctor 的四个检查项把提示硬编码成 `qa_agent.py init-project --repo .`——
缺 python 前缀也缺路径，用户照抄得到 command not found。工具自己的输出给出
一条跑不通的命令，比文档里写错更糟：这里就是他们看到「下一步」的地方。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import qa_agent
from qa_agent import self_invocation


def test_self_invocation_is_runnable(monkeypatch):
    monkeypatch.delenv("QA_AGENT_CLI", raising=False)

    cmd = self_invocation()

    assert cmd.startswith("python"), f"应以 python 开头，实际：{cmd!r}"
    assert "qa_agent.py" in cmd, f"应指向 CLI 脚本，实际：{cmd!r}"


def test_qa_agent_cli_env_wins(monkeypatch):
    monkeypatch.setenv("QA_AGENT_CLI", "/custom/ming-qa")

    assert self_invocation() == "/custom/ming-qa"


def test_no_bare_script_name_in_doctor_actions():
    """提示里不得出现不带 python 与路径的裸脚本名。"""
    src = Path(qa_agent.__file__).read_text(encoding="utf-8")
    lines = [l for l in src.splitlines()
             if "next_action" in l and "qa_agent.py init-project" in l]
    assert not lines, f"仍有硬编码的裸命令：{lines}"
