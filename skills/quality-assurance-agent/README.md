# quality-assurance-agent

端到端 QA 验收编排器，本工具包的**顶层路由 skill**。

本目录是 8 个 skill 中的主 skill，同时承载 Python CLI（`scripts/qa_agent.py`）。
7 个阶段子 skill 是它的下游：`qa-context-profiler`、`qa-risk-analyzer`、
`qa-testcase-designer`、`qa-test-script-generator`、`qa-test-runner`、
`qa-code-reviewer`、`qa-report-generator`。

## 安装

请从仓库根目录的 [README](../../README.md) 开始。这里只重复关键信息：

```bash
npx skills add mingdui/ming-qa -g
# 或
/plugin marketplace add mingdui/ming-qa
```

非交互安装（脚本化 / CI）的两个坑，完整写法见
[docs/installation.md](../../docs/installation.md) 的「非交互安装」一节：

- `--agent` 取值是 **`claude-code`**，不是 `claude`
- `--skill` 只接受单个精确名称，不支持逗号或 `*`（`*` 会被当文件系统通配符展开），
  要装多个就重复写 `-s`

## CLI 调用约定

本目录及 7 个子 skill 的文档里出现的 `ming-qa <cmd>`，指的是本目录下的
`scripts/qa_agent.py`，按以下优先级解析：

1. `$QA_AGENT_CLI` 环境变量
2. PATH 上的 `ming-qa`（把本 skill 的 `bin/` 目录加入 PATH 后可用）
3. 本目录内的 `scripts/qa_agent.py`

例如 `ming-qa doctor --repo .` 在没有全局命令时等价于：

```bash
python /path/to/quality-assurance-agent/scripts/qa_agent.py doctor --repo .
```

## 工作流

```
上下文收集 → 风险分析 → 用例设计 → 【用户确认】 → 脚本生成 → 执行与修复 → 代码审查 → 报告
```

用例确认是整个流程**唯一的人工门禁**，其余阶段自动衔接。

## 本目录内容

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 路由器本体：阶段编排、门禁规则、禁令 |
| `scripts/qa_agent.py` | CLI 单一真源，44 个子命令 |
| `scripts/qa_core/` | CLI 的辅助模块 |
| `references/` | 各阶段的详细契约（用例 schema、门禁、报告格式等） |
| `assets/` | 配置模板、报告模板、Playwright agents 定义 |
| `tests/` | pytest 测试套件 |
| `install.sh` / `install.ps1` | 从源码安装到 skills 目录（不改 shell 配置） |
| `RELEASE.md` | 发版流程 |
| `USAGE.md` | 详细使用说明 |

## 详细文档

安装、配置、架构的完整说明在仓库的 `docs/` 下：

- [安装](../../docs/installation.md)
- [配置](../../docs/configuration.md) —— 含 `notify.webhook` 与 LLM 网关配置
- [架构](../../docs/architecture.md)

## 隐私

本工具**不内置任何默认外部服务地址**。未配置时不发起任何网络请求：

- LLM 网关：默认未配置，多模型交叉审查会跳过
- 告警 webhook：默认为空，不发送任何通知

## 许可证

[MIT](../../LICENSE)
