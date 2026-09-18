# QA Agent

中文文档 | [English](README.en.md)

端到端 QA 验收工具包，以 **Agent Skill** 形式分发。把一次功能验收拆成固定阶段，
从上下文收集一路推进到报告收口，**只在用例确认时停下等你审核**。

支持 Claude Code、Codex、Cursor 及任何遵循 `SKILL.md` 规范的 agent。

```
上下文收集 → 风险分析 → 用例设计 → 【你来确认】 → 脚本生成 → 执行与修复 → 代码审查 → 报告
```

## 安装

```bash
# 方式一（推荐）：跨 agent，支持 40+ 种
npx skills add mingdui/ming-qa -g

# 方式二：Claude Code 官方插件市场
/plugin marketplace add mingdui/ming-qa
/plugin install ming-qa@ming-qa

# 方式三：从源码（离线环境 / 自定义安装位置）
git clone https://github.com/mingdui/ming-qa.git
cd ming-qa/skills/quality-assurance-agent && ./install.sh --target claude-code
```

三种方式都**不会修改你的 shell 配置文件**。
CLI 的调用方式与故障排除见 [docs/installation.md](docs/installation.md)。

<details>
<summary>非交互安装（脚本化 / CI）</summary>

```bash
npx skills add mingdui/ming-qa --agent claude-code --yes   -s quality-assurance-agent -s qa-context-profiler -s qa-risk-analyzer   -s qa-testcase-designer -s qa-test-script-generator -s qa-test-runner   -s qa-code-reviewer -s qa-report-generator
```

- agent 的取值是 **`claude-code`**，不是 `claude`（传 `claude` 会直接报
  `Invalid agents` 并中止）。
- `--skill` 一次只接受**一个精确名称**：不支持逗号分隔，也不支持 `*` 通配符
  ——CLI 会把 `*` 当成**文件系统**通配符在你当前目录展开，于是报出
  `No matching skills found for: AGENTS.md, src, …` 这种看似不相干的错误。
  要装多个就重复写 `-s`。

</details>

## 快速上手

装完之后**不需要敲任何命令**。在 Claude Code / Codex 里说：

```
使用 quality-assurance-agent，对 <你的模块> 进行验收
```

agent 会自动完成初始化、环境体检和工具链安装，只在需要你配合的三处停下：

1. **填配置** —— 它会告诉你缺哪几项、各自去哪填（`.qa-agent/local/.env`，已 git-ignored）。
   必填的只有测试账号；LLM Key 是可选的交叉审查增强，不填则该阶段跳过
2. **确认用例** —— 用例生成后停下等你审核。这是全流程**唯一的人工门禁**
3. 确认之后，脚本生成 → 执行修复 → 代码审查 → 报告，全部自动衔接

### 想手动跑命令

CLI 在 skill 的 `scripts/qa_agent.py`，**不作为 PATH 命令分发**。手动调用时先解析目录：

```bash
QA_AGENT_DIR="${QA_AGENT_CLI:-$(dirname "$(find ~/.claude/skills ~/.agents/skills ~/.codex/skills .claude/skills .agents/skills .codex/skills -maxdepth 2 -name SKILL.md -path '*quality-assurance-agent/*' 2>/dev/null | head -1)")}"
python "$QA_AGENT_DIR/scripts/qa_agent.py" doctor --repo . --strict --check-services
```


## 产物在哪

所有产物在目标项目的 `.qa-agent/` 下。

| 目录 | 内容 | git clone 后 |
|---|---|---|
| `.qa-agent/cases/` | 已确认的长期用例 | ✅ |
| `.qa-agent/spec-tasks/` | 用例→脚本映射蓝图 | ✅ |
| `.qa-agent/config/` | 项目 QA 配置 | ✅ |
| `.qa-agent/fixtures/` | 账号/服务示例模板 | ✅ |
| `.qa-agent/knowledge/` | 项目经验库 | ✅ |
| `.qa-agent/reports/` | HTML 报告 | ✅ |
| `.qa-agent/current/` | 本轮运行产物 | ❌ 需重新生成 |
| `.qa-agent/runs/` | 执行日志与证据 | ❌ |
| `.qa-agent/local/` | 本地账号密码 | ❌ |
| `tests/api/<模块>/` | 测试脚本 | ✅ |

> **git clone 后首次回归**：`current/` 丢失是正常的。先跑 `init-project` 建目录，
> 再执行 `generate-spec-tasks --acceptance-mode` 从 `cases/` 重新生成
> `test-spec-tasks.json`。`tests/api/` 下的脚本不受影响。

## 隐私与外发

**本工具不内置任何默认外部服务地址，也不会向任何默认地址发送数据。**

- **LLM 网关**：默认未配置。多模型交叉审查是可选增强，未配置时该阶段跳过，
  不中断流程，也不发起任何请求。
- **告警 webhook**：默认为空。不配置则不发通知、不产生网络请求。

详见 [docs/configuration.md](docs/configuration.md)。

## 系统要求

- Python 3.9+（仅用标准库，无第三方运行时依赖）
- Git
- 目标项目按验收范围需要 Java 21 / Maven 或 Node.js 20+

## 文档

- [安装](docs/installation.md)
- [配置](docs/configuration.md)
- [架构](docs/architecture.md)
- [贡献指南](CONTRIBUTING.md)
- [变更日志](CHANGELOG.md)

## 许可证

[MIT](LICENSE)
