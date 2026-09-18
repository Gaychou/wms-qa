#!/usr/bin/env python3
"""回归测试：SKILL.md 里的 skill 文档路径必须能被 agent 解析到真实文件。

历史缺陷（两轮，同一类）：

  第一轮：子 skill 里写 `.claude/skills/quality-assurance-agent/references/xxx.md`。
          但 npx skills 把技能装到 ~/.agents/skills/，只链接进全局 ~/.claude/skills/，
          项目里的 .claude/skills/ 并没有这个目录——从项目 cwd 出发根本不存在。

  第二轮：上一轮把这些改成了 `quality-assurance-agent/references/xxx.md`，
          少写了锚点。这个路径只有「cwd 恰好等于 skills 安装根」时才成立，
          而 QA_AGENT_DIR 的查找覆盖 ~/.claude/skills、~/.agents/skills、
          .claude/skills 等 6 个位置——**根本不存在一个固定的 skills 根**。

两轮的后果一样：agent 读不到参考文档，而且**不报错**，只是静默丢失上下文。

所以本测试不比对字符串，而是**真的解析路径**，断言落地文件存在：

  - `$QA_AGENT_DIR/...`        → 相对主 skill 目录解析
  - 裸相对路径 `references/...` → 相对该 SKILL.md 自己所在目录解析

skills 根**不是**允许的解析基准——那正是第二轮漏网的写法。
"""

import re
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
MAIN_SKILL_DIR = _TESTS_DIR.parent
SKILLS_ROOT = MAIN_SKILL_DIR.parent

# backtick 包裹、以 .md 结尾的路径
_DOC_REF = re.compile(r"`([^`\n]*?\.md)`")

# 只校验「skill 文档」引用。项目内的产物文档（AGENTS.md 等）不属于本测试范围。
_SKILL_DOC_MARKERS = ("references/", "$QA_AGENT_DIR",
                      ".claude/skills", ".agents/skills", ".codex/skills")


def _skill_docs():
    return sorted(SKILLS_ROOT.glob("*/SKILL.md"))


def _is_skill_doc_ref(ref):
    return any(marker in ref for marker in _SKILL_DOC_MARKERS)


def _resolve(ref, skill_dir):
    """把文档引用解析成磁盘路径。跨 skill 引用必须走 $QA_AGENT_DIR。"""
    if ref.startswith("$QA_AGENT_DIR/"):
        return MAIN_SKILL_DIR / ref[len("$QA_AGENT_DIR/"):]
    return skill_dir / ref


def test_skill_doc_paths_resolve():
    problems = []
    checked = 0

    for skill_md in _skill_docs():
        text = skill_md.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            for ref in _DOC_REF.findall(line):
                if not _is_skill_doc_ref(ref):
                    continue
                checked += 1
                target = _resolve(ref, skill_md.parent)
                if target.exists():
                    continue
                hint = ""
                if ref.startswith(("quality-assurance-agent/", ".claude/skills")):
                    hint = "（跨 skill 引用请写成 `$QA_AGENT_DIR/references/...`）"
                problems.append(
                    f"{skill_md.relative_to(SKILLS_ROOT)}:{lineno} "
                    f"`{ref}` → {target} 不存在{hint}"
                )

    # 防止正则或目录结构变化导致的「空跑通过」
    assert checked >= 15, (
        f"只检查到 {checked} 处 skill 文档引用，测试可能已失去判别力"
    )
    assert not problems, "有 agent 解析不到的 skill 文档路径：\n  " + "\n  ".join(problems)


def test_no_raw_agent_install_path_in_skills():
    """不得写死 agent 安装目录——安装位置因工具而异，只有解析出的变量才可靠。

    QA_AGENT_DIR 的 find 查找命令本身要列出这些目录，那是唯一允许出现的地方。
    """
    offenders = []
    for skill_md in _skill_docs():
        text = skill_md.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if "find " in line:  # 变量定义里的目录探测
                continue
            for marker in (".claude/skills/", ".agents/skills/", ".codex/skills/"):
                if marker in line:
                    offenders.append(
                        f"{skill_md.relative_to(SKILLS_ROOT)}:{lineno} 含写死路径 {marker}"
                    )
    assert not offenders, "写死了 agent 安装目录：\n  " + "\n  ".join(offenders)
