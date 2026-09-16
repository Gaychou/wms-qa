"""Shared pytest fixtures for the quality-assurance-agent CLI and qa_core."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SKILL_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = _SKILL_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def load_qa_agent() -> object:
    """Load scripts/qa_agent.py without executing its main block."""
    spec = importlib.util.spec_from_file_location("qa_agent", _SCRIPTS_DIR / "qa_agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.fixture(scope="session")
def qa() -> object:
    return load_qa_agent()


@pytest.fixture
def make_repo(tmp_path):
    """Factory creating a fake repo root with optional module/project files."""
    def _make(files: dict[str, str] | None = None) -> Path:
        repo = tmp_path / "repo"
        repo.mkdir(exist_ok=True)
        return repo

    return _make
