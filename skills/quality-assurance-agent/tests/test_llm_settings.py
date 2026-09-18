#!/usr/bin/env python3
"""回归测试：llm 配置段要真的生效。

历史缺陷：`qa-agent.config.yaml` 模板里写着完整的 llm 段（baseUrlEnv / apiKeyEnv /
defaultBaseUrl / models / timeoutSeconds），`docs/configuration.md` 也照它写了一份
说明——但 `load_config()` 的取值只用到 repair / playwright / notify / qualityGates，
**从来没读过 llm**。

后果：用户按文档把 `llm.models` 改成自己网关的模型名，实际仍走三个内置默认值，
静默无效、毫无提示。用户想接自己的模型却怎么改都不对。

这里钉住：配置生效、CLI 覆盖配置、「没传参」与「传了值」可区分。
"""

import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import DEFAULT_MODELS, resolve_llm_settings

CONFIG = """
llm:
  baseUrlEnv: "MY_BASE_URL_ENV"
  apiKeyEnv: "MY_KEY_ENV"
  defaultBaseUrl: "https://my-gateway.example.com/api"
  models:
    - "my-model-a"
    - "my-model-b"
  timeoutSeconds: 42
  stream: false
"""


def _repo_with_config(tmp_path: Path, body: str = CONFIG) -> Path:
    cfg = tmp_path / ".qa-agent" / "config"
    cfg.mkdir(parents=True)
    (cfg / "qa-agent.config.yaml").write_text(body, encoding="utf-8")
    return tmp_path


def _args(**over) -> argparse.Namespace:
    """模拟 CLI：默认值一律 None，表示「没传」。"""
    base = dict(config=None, models=None, base_url=None, base_url_env=None,
                api_key_env=None, timeout=None, stream=None)
    base.update(over)
    return argparse.Namespace(**base)


def test_config_section_is_actually_read(tmp_path, monkeypatch):
    """配置文件里的 llm 段必须生效——这是本测试存在的理由。"""
    repo = _repo_with_config(tmp_path)
    monkeypatch.chdir(repo)

    llm = resolve_llm_settings(_args())

    assert llm["models"] == ["my-model-a", "my-model-b"], (
        "配置里的 llm.models 没生效——用户改了自己的模型名却仍走内置默认值"
    )
    assert llm["baseUrlEnv"] == "MY_BASE_URL_ENV"
    assert llm["apiKeyEnv"] == "MY_KEY_ENV"
    assert llm["baseUrl"] == "https://my-gateway.example.com/api"
    assert llm["timeout"] == 42
    assert llm["stream"] is False


def test_cli_overrides_config(tmp_path, monkeypatch):
    repo = _repo_with_config(tmp_path)
    monkeypatch.chdir(repo)

    llm = resolve_llm_settings(_args(models="cli-model", timeout=7, stream=True))

    assert llm["models"] == ["cli-model"]
    assert llm["timeout"] == 7
    assert llm["stream"] is True


def test_stream_defaults_to_true_without_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # 没有配置文件

    llm = resolve_llm_settings(_args())

    assert llm["stream"] is True, "无配置时默认流式"
    assert llm["models"] == list(DEFAULT_MODELS)
    assert llm["timeout"] == 300


def test_explicit_config_path(tmp_path, monkeypatch):
    repo = _repo_with_config(tmp_path)
    monkeypatch.chdir(tmp_path.parent)

    llm = resolve_llm_settings(_args(config=str(repo / ".qa-agent" / "config" / "qa-agent.config.yaml")))

    assert llm["models"] == ["my-model-a", "my-model-b"]


def test_corrupt_config_falls_back_instead_of_crashing(tmp_path, monkeypatch):
    repo = _repo_with_config(tmp_path, "llm: [this is not a mapping")
    monkeypatch.chdir(repo)

    llm = resolve_llm_settings(_args())

    assert llm["models"] == list(DEFAULT_MODELS), "配置坏了应回退默认值而不是让审查崩掉"
    assert llm["stream"] is True


def test_empty_models_list_falls_back(tmp_path, monkeypatch):
    repo = _repo_with_config(tmp_path, 'llm:\n  models: []\n')
    monkeypatch.chdir(repo)

    llm = resolve_llm_settings(_args())

    assert llm["models"] == list(DEFAULT_MODELS)
