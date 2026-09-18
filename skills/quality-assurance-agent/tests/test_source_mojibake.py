#!/usr/bin/env python3
"""仓库自己的文本文件不得含替换字符（U+FFFD）。

为什么单独有这个测试：本工具内置了 `check-mojibake` 门禁，会拿它去查用户项目的
产物——但**从没查过自己的源码**。实测因此在 `qa_agent.py` 里发现两处：

  1. SC-002 文档字符串里的「与」被打成了替换字符（可读性受损）
  2. `if ch == "\\ufffd"` 的转义写法在保存过程中变成了真实字符
     （功能上等价，但让整个文件过不了自己的门禁）

工具自己的门禁不查自己，是个说不通的盲区。这个测试把它补上。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

REPO_ROOT = Path(__file__).parent.parent.parent.parent
TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".sh", ".ps1", ".cmd", ".txt"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", "docs"}
REPLACEMENT_CHARACTER = "\ufffd"


def _text_files():
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def test_no_mojibake_in_repo_text_files():
    """任何一个仓库文本文件含 U+FFFD 都算失败，并指出具体位置。"""
    offenders: list[str] = []
    scanned = 0

    for path in _text_files():
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            offenders.append(f"{path.relative_to(REPO_ROOT)}: 不是合法 UTF-8")
            continue
        if REPLACEMENT_CHARACTER not in text:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if REPLACEMENT_CHARACTER in line:
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()[:80]}")

    assert scanned > 20, f"只扫到 {scanned} 个文件，路径推断可能不对"
    assert not offenders, (
        "源码里出现替换字符 U+FFFD——文本在保存过程中损坏了：\n  " + "\n  ".join(offenders[:20])
    )
