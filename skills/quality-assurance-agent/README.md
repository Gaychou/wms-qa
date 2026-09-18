# quality-assurance-agent

端到端 QA 验收编排器，本工具包的**顶层路由 skill**。

本目录是 8 个 skill 中的主 skill，同时承载 Python CLI（`scripts/qa_agent.py`）。
7 个阶段子 skill 是它的下游：`qa-context-profiler`、`qa-risk-analyzer`、
`qa-testcase-designer`、`qa-test-script-generator`、`qa-test-runner`、
`qa-code-reviewer`、`qa-report-generator`。

## 安装

请从仓库根目录的 [README](../../README.md) 开始。

```bash
npx skills add mingdui/ming-qa -g
# 或
/plugin marketplace add mingdui/ming-qa
```

脚本化安装（CI）的完整写法见 [安装文档](../../docs/installation.md)。

## 工作流

```
上下文收集 → 风险分析 → 用例设计 → 【用户确认】 → 脚本生成 → 执行与修复 → 代码审查 → 报告
```

用例确认是整个流程**唯一的人工门禁**，其余阶段自动衔接。

## CLI 调用约定

本目录及 7 个子 skill 的文档里，命令一律通过 `scripts/qa_agent.py` 执行。
先解析一次 skill 目录，之后所有命令写成 `python "$QA_AGENT_DIR/scripts/qa_agent.py" <cmd>`：

```bash
QA_AGENT_DIR="${QA_AGENT_CLI:-$(dirname "$(find ~/.claude/skills ~/.agents/skills ~/.codex/skills .claude/skills .agents/skills .codex/skills -maxdepth 2 -name SKILL.md -path '*quality-assurance-agent/*' 2>/dev/null | head -1)")}"
```

## 本目录内容

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 路由器本体：阶段编排、门禁规则、禁令 |
| `scripts/qa_agent.py` | CLI 单一真源 |
| `scripts/qa_core/` | CLI 的辅助模块 |
| `references/` | 各阶段的详细契约（用例 schema、门禁、报告格式等） |
| `assets/` | 配置模板、报告模板、Playwright agents 定义 |
| `tests/` | pytest 测试套件 |
| `install.sh` / `install.ps1` | 从源码安装到 skills 目录（不改 shell 配置） |
| `RELEASE.md` | 发版流程 |
| `USAGE.md` | 详细使用说明 |

## 数据与外发

本工具不内置任何外部服务地址，只在你明确配置后才对外通信：

- LLM 网关 —— 用于可选的多模型交叉审查，未配置则跳过
- 告警 webhook —— 用于推送报告质量告警，未配置则不发送

配置方式见 [配置文档](../../docs/configuration.md)。

## 许可证

[MIT](../../LICENSE)
