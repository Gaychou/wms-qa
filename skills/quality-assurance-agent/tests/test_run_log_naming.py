"""测试 run log 文件名与解析正则的一致性"""
import re
import time
from pathlib import Path


# 从 qa_agent.py 复制正则
_RUN_LOG_NAME_RE = re.compile(
    r"^run(?:-task-(?P<task_order>\d+))?-(?P<case_id>tc-p\d+-\d+)-(?P<slug>[a-z0-9\-]+?)-(?P<epoch>\d{10,})\.log$",
    re.IGNORECASE,
)


def test_generated_filename_matches_regex():
    """验证生成的文件名能被解析正则匹配"""
    # 模拟当前生成逻辑
    script_stem = "tc-p0-001"
    epoch = int(time.time())
    old_filename = f"run-{script_stem}-{epoch}.log"

    # 旧格式无法匹配
    assert _RUN_LOG_NAME_RE.match(old_filename) is None, "旧格式不应该匹配"

    # 新格式：补充 slug 段
    case_id = "tc-p0-001"
    slug = "order-flow"  # 应该从脚本名或用例中提取
    new_filename = f"run-{case_id}-{slug}-{epoch}.log"

    # 新格式能匹配
    match = _RUN_LOG_NAME_RE.match(new_filename)
    assert match is not None, "新格式应该匹配"
    assert match.group("case_id").upper() == case_id.upper()
    assert match.group("slug") == slug
    assert int(match.group("epoch")) == epoch


def test_filename_with_task_order():
    """验证带 task_order 的文件名"""
    case_id = "tc-p0-001"
    slug = "order"
    task_order = 3
    epoch = int(time.time())

    filename = f"run-task-{task_order}-{case_id}-{slug}-{epoch}.log"
    match = _RUN_LOG_NAME_RE.match(filename)

    assert match is not None
    assert int(match.group("task_order")) == task_order
    assert match.group("case_id").upper() == case_id.upper()
    assert match.group("slug") == slug


def test_slug_extraction_from_stem():
    """验证如何从 script_stem 提取 slug"""
    # script_stem 可能的格式：
    # - tc-p0-001.sh -> slug 应该是 "default" 或从用例 title 提取
    # - tc-p0-001-order-flow.sh -> slug 是 "order-flow"
    # - task-3-tc-p0-001-order.sh -> slug 是 "order"

    test_cases = [
        ("tc-p0-001", "tc-p0-001", None, "default"),  # 只有 case_id，slug 用 default
        ("tc-p0-001-order", "tc-p0-001", None, "order"),  # case_id + slug
        ("task-3-tc-p0-001-order", "tc-p0-001", 3, "order"),  # 带 task_order
    ]

    for stem, expected_case_id, expected_task_order, expected_slug in test_cases:
        # 解析 script_stem
        parts = stem.split("-")

        if parts[0] == "task":
            # 格式：task-N-tc-pX-NNN-<slug>
            task_order = int(parts[1])
            case_id = f"{parts[2]}-{parts[3]}-{parts[4]}"
            slug = "-".join(parts[5:]) if len(parts) > 5 else "default"
        elif parts[0].lower() == "tc":
            # 格式：tc-pX-NNN 或 tc-pX-NNN-<slug>
            case_id = f"{parts[0]}-{parts[1]}-{parts[2]}"
            slug = "-".join(parts[3:]) if len(parts) > 3 else "default"
            task_order = None
        else:
            continue

        assert case_id == expected_case_id
        assert task_order == expected_task_order
        assert slug == expected_slug
