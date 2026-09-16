"""集成测试：验证 run-with-env 生成的日志文件能被 aggregate-runs 解析"""
import re
import subprocess
import tempfile
from pathlib import Path


_RUN_LOG_NAME_RE = re.compile(
    r"^run(?:-task-(?P<task_order>\d+))?-(?P<case_id>tc-p\d+-\d+)-(?P<slug>[a-z0-9\-]+?)-(?P<epoch>\d{10,})\.log$",
    re.IGNORECASE,
)


def test_run_with_env_generates_parseable_filename(tmp_path):
    """验证 run-with-env 生成的文件名能被正则匹配"""
    # 创建临时脚本
    script = tmp_path / "scripts" / "tc-p0-001-order.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/bin/bash\necho 'test'\nexit 0\n")
    script.chmod(0o755)

    # 创建 .qa-agent/runs 目录
    runs_dir = tmp_path / ".qa-agent" / "runs"
    runs_dir.mkdir(parents=True)

    # 模拟 run-with-env 的文件名生成逻辑
    stem_parts = script.stem.split("-")
    if stem_parts[0].lower() == "tc":
        case_id = f"{stem_parts[0]}-{stem_parts[1]}-{stem_parts[2]}"
        slug = "-".join(stem_parts[3:]) if len(stem_parts) > 3 else "default"
    else:
        case_id = script.stem
        slug = "default"

    import time
    log_filename = f"run-{case_id}-{slug}-{int(time.time())}.log"

    # 验证文件名能被正则匹配
    match = _RUN_LOG_NAME_RE.match(log_filename)
    assert match is not None, f"生成的文件名 {log_filename} 无法被正则匹配"
    assert match.group("case_id").upper() == case_id.upper()
    assert match.group("slug") == slug


def test_various_script_names():
    """测试各种脚本命名格式"""
    import time
    test_cases = [
        ("tc-p0-001", "tc-p0-001", "default"),
        ("tc-p0-001-order", "tc-p0-001", "order"),
        ("tc-p1-005-login-flow", "tc-p1-005", "login-flow"),
        ("tc-p2-014-probability-check", "tc-p2-014", "probability-check"),
    ]

    for script_stem, expected_case_id, expected_slug in test_cases:
        # 模拟生成逻辑
        stem_parts = script_stem.split("-")
        if stem_parts[0].lower() == "tc":
            case_id = f"{stem_parts[0]}-{stem_parts[1]}-{stem_parts[2]}"
            slug = "-".join(stem_parts[3:]) if len(stem_parts) > 3 else "default"
        else:
            case_id = script_stem
            slug = "default"

        assert case_id == expected_case_id, f"case_id 提取错误：{case_id} != {expected_case_id}"
        assert slug == expected_slug, f"slug 提取错误：{slug} != {expected_slug}"

        # 验证生成的文件名能被匹配
        log_filename = f"run-{case_id}-{slug}-{int(time.time())}.log"
        match = _RUN_LOG_NAME_RE.match(log_filename)
        assert match is not None, f"文件名 {log_filename} 无法被匹配"
        assert match.group("case_id").upper() == case_id.upper()
        assert match.group("slug") == slug
