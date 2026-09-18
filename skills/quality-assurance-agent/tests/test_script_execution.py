#!/usr/bin/env python3
"""回归测试：跑脚本 / 跑配置命令时的解释器选择、引号解析与环境加载。

三处历史缺陷，都是使用者实际撞到的：

  ① `run-with-env` 一律用 bash 执行，不看扩展名。`.py` 脚本被 bash 当 shell 解析：

         .../xxx.py: line 16: import: command not found
         .../xxx.py: line 36: syntax error near unexpected token `('

     使用者只能自己再写一层 `.sh` 包装来 exec python。

  ② `parse_scalar` 只剥双引号、不剥单引号，而 `yaml_quote()` 生成配置时用
     json.dumps 产出双引号——生成端与解析端不对称。使用者手写 `'cmd'` 时引号被原样
     留下，传给 cmd.exe 报 `''cd' 不是内部或外部命令`。同一个不对称还让含 `:` 的
     单引号列表项被误判成字典。

  ③ `run-commands` / `run-gate` 不加载 `.qa-agent` 的 .env，而 `run-with-env` 会。
     依赖数据库凭证的门禁命令第一次跑必然失败（QA_MYSQL_USER 为空），且两处行为
     不一致又没有文档提示。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest


# ── ① 解释器按扩展名选 ──────────────────────────────────────────────────


def test_py_script_uses_current_interpreter(qa):
    """`.py` 用跑本 CLI 的解释器，不用 PATH 里的 python（Windows 上可能是 Store 占位）。"""
    argv = qa.interpreter_argv_for_script(Path("tests/api/x.py"))

    assert argv[0] == sys.executable
    assert argv[-1].endswith("x.py")


def test_shell_script_uses_bash(qa, monkeypatch):
    monkeypatch.setattr(qa.shutil, "which", lambda name: "/usr/bin/bash")
    argv = qa.interpreter_argv_for_script(Path("tests/api/x.sh"))

    assert argv[0] == "/usr/bin/bash"


def test_unknown_extension_falls_back_to_shell(qa, monkeypatch):
    """未知扩展名保持既有行为（走 shell），不做破坏性变更。"""
    monkeypatch.setattr(qa.shutil, "which", lambda name: "/usr/bin/bash")
    argv = qa.interpreter_argv_for_script(Path("tests/api/run.xyz"))

    assert argv[0] == "/usr/bin/bash"


def test_js_without_node_raises_readable_error(qa, monkeypatch):
    monkeypatch.setattr(qa.shutil, "which", lambda name: None)

    with pytest.raises(qa.QaAgentError) as exc:
        qa.interpreter_argv_for_script(Path("tests/api/x.js"))

    assert "node" in str(exc.value)


# --- ② 引号解析与生成端对称 ---


def test_single_quoted_value_is_unquoted(qa):
    assert qa.parse_scalar("'cd x && mvn test'") == "cd x && mvn test"


def test_single_quote_escape_is_a_literal_quote(qa):
    """YAML 单引号里写 '' 表示一个字面单引号。"""
    assert qa.parse_scalar("'it''s'") == "it's"


def test_quoted_numbers_stay_strings(qa):
    assert qa.parse_scalar("'1'") == "1"
    assert qa.parse_scalar('"1"') == "1"
    assert qa.parse_scalar("1") == 1


def test_yaml_quote_round_trips(qa):
    """generate 用的 yaml_quote 与 parse_scalar 必须能来回转。"""
    for value in ["cd x && mvn test", 'has "double" quotes', "has 'single' quotes", "中文 参数"]:
        assert qa.parse_scalar(qa.yaml_quote(value)) == value, f"round-trip 失败：{value!r}"


def test_quoted_list_item_with_colon_is_a_command(qa):
    """含 `:` 的单引号列表项是命令，不是字典。"""
    parsed = qa.parse_simple_yaml("commands:\n  api:\n    - 'curl http://x/y && echo ok'\n")

    assert parsed["commands"]["api"] == ["curl http://x/y && echo ok"]


def test_quoted_command_with_colon_keeps_its_colon(qa):
    """双引号形式同理（生成端产出的就是这种）。"""
    parsed = qa.parse_simple_yaml("commands:\n  api:\n    - \"mvn -Durl=http://x test\"\n")

    assert parsed["commands"]["api"] == ["mvn -Durl=http://x test"]


# ── ③ 门禁命令与 run-with-env 加载同一份 .env ────────────────────────────


def _repo_with_env(tmp_path):
    shared = tmp_path / ".qa-agent" / "config" / "env.shared"
    shared.parent.mkdir(parents=True, exist_ok=True)
    shared.write_text("QA_MYSQL_USER=shared_user\nQA_MYSQL_HOST=192.0.2.10\n", encoding="utf-8")
    local = tmp_path / ".qa-agent" / "local" / ".env"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text("QA_MYSQL_USER=local_user\n", encoding="utf-8")
    return tmp_path


def test_gate_env_loads_layered_env(qa, tmp_path, monkeypatch):
    """门禁命令要能拿到 .env 里的凭证，否则依赖数据库的命令必然失败。"""
    repo = _repo_with_env(tmp_path)
    monkeypatch.delenv("QA_MYSQL_USER", raising=False)
    monkeypatch.delenv("QA_MYSQL_HOST", raising=False)

    env = qa.gate_env(repo)

    assert env["QA_MYSQL_USER"] == "local_user", "local/.env 应覆盖 env.shared"
    assert env["QA_MYSQL_HOST"] == "192.0.2.10"


def test_gate_env_keeps_process_environment(qa, tmp_path):
    """只做叠加，不裁掉进程原有的环境变量。"""
    repo = _repo_with_env(tmp_path)
    env = qa.gate_env(repo)

    assert "PATH" in env or "Path" in env


def test_gate_env_matches_run_with_env_source(qa, tmp_path, monkeypatch):
    """两者必须读同一份 .env——历史上只有 run-with-env 读，就是这个不一致造成的。"""
    repo = _repo_with_env(tmp_path)
    monkeypatch.delenv("QA_MYSQL_USER", raising=False)

    assert qa.gate_env(repo)["QA_MYSQL_USER"] == qa._load_env(repo)["QA_MYSQL_USER"]


def _capture_run_cmd(qa, monkeypatch):
    captured = {}

    def fake_run_cmd(command, cwd, **kwargs):
        captured["env"] = kwargs.get("env")
        return {"command": str(command), "cwd": str(cwd), "exitCode": 0,
                "durationSeconds": 0.0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(qa, "run_cmd", fake_run_cmd)
    return captured


def test_run_commands_passes_env_to_each_command(qa, tmp_path, monkeypatch):
    """调用点必须真的把 .env 传下去——只验 gate_env() 自身会漏掉接线。"""
    repo = _repo_with_env(tmp_path)
    cfg = tmp_path / "qa-agent.config.yaml"
    cfg.write_text("commands:\n  api:\n    - \"echo hi\"\n", encoding="utf-8")
    captured = _capture_run_cmd(qa, monkeypatch)
    args = argparse.Namespace(repo=str(repo), config=str(cfg), gate="api", timeout=10,
                              continue_on_failure=False, output=str(tmp_path / "out.json"))

    qa.run_commands(args)

    assert captured["env"]["QA_MYSQL_USER"] == "local_user"
    assert captured["env"]["QA_MYSQL_HOST"] == "192.0.2.10"


def test_run_gate_passes_env_to_each_command(qa, tmp_path, monkeypatch):
    repo = _repo_with_env(tmp_path)
    captured = _capture_run_cmd(qa, monkeypatch)

    qa.run_gate(repo, "api", ["echo hi"], 10, False)

    assert captured["env"]["QA_MYSQL_USER"] == "local_user"
