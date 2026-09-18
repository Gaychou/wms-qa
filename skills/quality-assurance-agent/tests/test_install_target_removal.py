#!/usr/bin/env python3
"""回归测试：安装目标的删除要兼容普通目录 / 符号链接 / Windows junction。

背景：`install-skill --force` 遇到 npx skills 装出来的目标时崩溃——

    OSError: Cannot call rmtree on a symbolic link

坑在于 Windows 上 npx skills 建的是 **junction**（reparse tag MOUNT_POINT）。
`Path.is_symlink()` 和 `os.path.islink()` 对它都返回 False（lstat 看到的是目录），
但 `shutil.rmtree()` 会直接抛上面那个错。所以「先判断是不是链接」的分支写法
必然漏掉 junction——只能对 rmtree 的失败兜底。

关键约束：删除链接时**绝不能递归进真身**。真身是 .agents/skills 下的另一份安装。
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from qa_agent import _remove_install_target


def test_removes_real_directory(tmp_path):
    target = tmp_path / "skill"
    (target / "scripts").mkdir(parents=True)
    (target / "scripts" / "a.py").write_text("x = 1", encoding="utf-8")

    _remove_install_target(target)

    assert not target.exists()


def test_removes_symlink_without_touching_target(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "keep.txt").write_text("keep", encoding="utf-8")
    link = tmp_path / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("该环境下无法创建符号链接")

    _remove_install_target(link)

    assert not link.exists(), "链接应被删除"
    assert real.exists(), "真身不能被删"


def test_removes_windows_junction_without_touching_target(tmp_path):
    """本测试存在的理由：junction 的 is_symlink() 是 False，只能靠 rmtree 失败兜底。"""
    if os.name != "nt":
        pytest.skip("junction 是 Windows 特有")

    real = tmp_path / "real"
    real.mkdir()
    (real / "keep.txt").write_text("keep", encoding="utf-8")
    junction = tmp_path / "junction"

    made = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(real)],
        capture_output=True, text=True,
    )
    if made.returncode != 0 or not junction.exists():
        pytest.skip(f"无法创建 junction：{made.stdout or made.stderr}")

    # 前提确认：Python 不认为它是链接，但 rmtree 会拒绝它
    assert junction.is_symlink() is False, "junction 不该被当成符号链接"

    _remove_install_target(junction)

    assert not junction.exists(), "junction 应被摘除"
    assert real.exists(), "真身不能被删"
    assert (real / "keep.txt").exists(), "真身里的文件不能丢"
