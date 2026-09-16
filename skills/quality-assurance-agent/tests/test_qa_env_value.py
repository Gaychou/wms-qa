"""测试 qa_env_value 分层读取：env.shared（团队共享）也能读到账号凭证。"""
from __future__ import annotations

import os


def test_qa_env_value_reads_env_shared(qa, tmp_path, monkeypatch):
    """账号维护在 config/env.shared 时，qa_env_value 应能读到（不再只读 local/.env）。"""
    shared = tmp_path / ".qa-agent" / "config" / "env.shared"
    shared.parent.mkdir(parents=True, exist_ok=True)
    shared.write_text(
        "QA_USER_USERNAME=test_user\nQA_USER_PASSWORD=test_pass\n",
        encoding="utf-8",
    )
    # 确保 os.environ 和 local/.env 都不覆盖
    monkeypatch.delenv("QA_USER_USERNAME", raising=False)
    monkeypatch.delenv("QA_USER_PASSWORD", raising=False)

    assert qa.qa_env_value(tmp_path, "QA_USER_USERNAME") == "test_user"
    assert qa.qa_env_value(tmp_path, "QA_USER_PASSWORD") == "test_pass"


def test_qa_env_value_local_overrides_shared(qa, tmp_path, monkeypatch):
    shared = tmp_path / ".qa-agent" / "config" / "env.shared"
    shared.parent.mkdir(parents=True, exist_ok=True)
    shared.write_text("QA_USER_USERNAME=shared_user\n", encoding="utf-8")
    local = tmp_path / ".qa-agent" / "local" / ".env"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text("QA_USER_USERNAME=local_user\n", encoding="utf-8")
    monkeypatch.delenv("QA_USER_USERNAME", raising=False)

    assert qa.qa_env_value(tmp_path, "QA_USER_USERNAME") == "local_user"


def test_qa_env_value_empty_when_unset(qa, tmp_path, monkeypatch):
    monkeypatch.delenv("QA_USER_USERNAME", raising=False)
    assert qa.qa_env_value(tmp_path, "QA_USER_USERNAME") == ""
