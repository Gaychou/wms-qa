"""验证 mysql_mcp 配置写入不会覆盖其他 MCP 配置。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _write_env(repo: Path) -> None:
    """写入 .qa-agent/local/.env 提供 MySQL 凭证。"""
    env = repo / ".qa-agent" / "local" / ".env"
    env.parent.mkdir(parents=True, exist_ok=True)
    env.write_text(
        "QA_MYSQL_HOST=127.0.0.1\n"
        "QA_MYSQL_USER=qa\n"
        "QA_MYSQL_PASS=secret\n"
        "QA_MYSQL_DATABASE=demo\n",
        encoding="utf-8",
    )


def test_upsert_mysql_mcp_entry_preserves_other_mcp_json(qa, tmp_path):
    """upsert_mysql_mcp_entry 只改 .mcp.json 的 mysql_mcp 键，保留其他 server。"""
    repo = tmp_path
    _write_env(repo)
    other = {
        "command": "npx",
        "args": ["-y", "@some/github-server"],
    }
    (repo / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"github": other}}, ensure_ascii=False),
        encoding="utf-8",
    )

    result = qa.upsert_mysql_mcp_entry(repo)
    assert result["generated"] is True

    mcp = json.loads((repo / ".mcp.json").read_text(encoding="utf-8"))
    assert "github" in mcp["mcpServers"], "其他 MCP 配置（github）被覆盖丢失"
    assert mcp["mcpServers"]["github"] == other
    assert "mysql_mcp" in mcp["mcpServers"]


def test_generate_codex_mysql_mcp_preserves_other_codex_mcp(qa, tmp_path):
    """generate_codex_mysql_mcp 只 upsert mysql_mcp 段，保留 .codex/config.toml 其他 MCP。"""
    repo = tmp_path
    _write_env(repo)
    codex_file = repo / ".codex" / "config.toml"
    codex_file.parent.mkdir(parents=True, exist_ok=True)
    codex_file.write_text(
        '[mcp_servers.github]\n'
        'command = "npx"\n'
        'args = ["-y", "@some/github-server"]\n\n'
        '# 用户手写的其他配置\n'
        'model = "claude-sonnet-5"\n',
        encoding="utf-8",
    )

    result = qa.generate_codex_mysql_mcp(repo)
    assert result["generated"] is True

    text = codex_file.read_text(encoding="utf-8")
    assert "[mcp_servers.github]" in text, "其他 MCP（github）被覆盖丢失"
    assert "[mcp_servers.mysql_mcp]" in text, "mysql_mcp 未写入"
    assert "model = " in text, "用户手写的其他配置被覆盖丢失"


def test_generate_codex_mcp_from_project_preserves_other_codex_mcp(qa, tmp_path):
    """generate_codex_mcp_from_project 逐个 upsert，保留 .codex/config.toml 已有的其他 MCP。"""
    repo = tmp_path
    mcp_servers = {
        "mysql_mcp": {
            "command": "npx",
            "args": ["-y", "@executeautomation/database-server", "--mysql"],
        },
        "linear": {
            "command": "npx",
            "args": ["-y", "@some/linear-server"],
        },
    }
    (repo / ".mcp.json").write_text(
        json.dumps({"mcpServers": mcp_servers}, ensure_ascii=False),
        encoding="utf-8",
    )
    codex_file = repo / ".codex" / "config.toml"
    codex_file.parent.mkdir(parents=True, exist_ok=True)
    # 已有其他 MCP（不在 .mcp.json 里）
    codex_file.write_text(
        '[mcp_servers.github]\n'
        'command = "npx"\n'
        'args = ["-y", "@some/github-server"]\n',
        encoding="utf-8",
    )

    result = qa.generate_codex_mcp_from_project(repo)
    assert result["generated"] is True

    text = codex_file.read_text(encoding="utf-8")
    assert "[mcp_servers.github]" in text, "已有 github MCP 被覆盖丢失"
    assert "[mcp_servers.mysql_mcp]" in text, "mysql_mcp 未合并进去"
    assert "[mcp_servers.linear]" in text, "linear MCP 未合并进去"


def test_upsert_codex_mcp_server_replaces_only_target_section(qa, tmp_path):
    """upsert_codex_mcp_server 只替换目标段，保留其他段。"""
    config = tmp_path / "config.toml"
    config.write_text(
        '[mcp_servers.old]\n'
        'command = "old"\n\n'
        '[mcp_servers.mysql_mcp]\n'
        'command = "oldmysql"\n\n'
        '[mcp_servers.other]\n'
        'command = "other"\n',
        encoding="utf-8",
    )

    result = qa.upsert_codex_mcp_server(
        config, "mysql_mcp", {"command": "npx", "args": ["--mysql"]}
    )

    assert result["replaced"] is True
    text = config.read_text(encoding="utf-8")
    assert "[mcp_servers.old]" in text
    assert "[mcp_servers.other]" in text
    assert 'command = "npx"' in text, "mysql_mcp 未被替换为新值"
    assert 'command = "oldmysql"' not in text, "mysql_mcp 旧值残留"
