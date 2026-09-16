"""测试 _risk_candidate_files 的 --module 参数优先级"""
import pytest
from pathlib import Path
import tempfile
import shutil
from qa_agent import _risk_candidate_files


def test_module_parameter_has_priority():
    """验证 --module 参数优先于 git 文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        # 创建测试文件
        test_file = repo / "test.py"
        test_file.write_text("# test file")

        git_file = repo / "git_changed.py"
        git_file.write_text("# git changed")

        # 模拟 context 包含 git_changed.py（作为隐式回退）
        context = {"changedFiles": ["git_changed.py"]}

        # 显式传入 --module 应该只返回 test.py，忽略 git 文件
        result = _risk_candidate_files(repo, context, module=["test.py"])

        assert len(result) == 1
        assert result[0].name == "test.py"
        # 确保 git_changed.py 不在结果中
        assert not any(p.name == "git_changed.py" for p in result)


def test_module_parameter_empty_raises():
    """验证 --module 不匹配任何文件时抛出异常而非回退"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        git_file = repo / "git_changed.py"
        git_file.write_text("# git changed")

        context = {"changedFiles": ["git_changed.py"]}

        # --module 传了不存在的文件，应该抛异常而非回退到 git 文件
        with pytest.raises(Exception) as exc:
            _risk_candidate_files(repo, context, module=["nonexistent.py"])

        assert "未匹配到任何文件" in str(exc.value)


def test_no_module_falls_back_to_context():
    """验证未传 --module 时正确回退到 context"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        git_file = repo / "git_changed.py"
        git_file.write_text("# git changed")

        context = {"changedFiles": ["git_changed.py"]}

        # 未传 --module，应该使用 context
        result = _risk_candidate_files(repo, context, module=None)

        assert len(result) == 1
        assert result[0].name == "git_changed.py"
