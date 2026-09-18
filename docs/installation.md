# 安装

本工具以 **Agent Skill** 形式分发。装好之后由 agent 驱动，不需要自己敲命令。

## 安装方式

### 方式一：`npx skills`（推荐）

```bash
npx skills add mingdui/ming-qa -g -y
```

适用于 Claude Code、Codex、Cursor 等 40 多种 agent——技能装到通用的
`~/.agents/skills/`，再链接进本机所有已检测到的 agent。

`-y` 一次装全 8 个技能。不带它会进入交互选择，逐个挑比较麻烦。

`-g` 装到用户级目录，对所有项目生效；省略 `-g` 则装到当前项目。

默认用**符号链接**把技能链接进各 agent 的目录（单一事实来源，更新一次全部生效），
想改用复制加 `--copy`。

验证：

```bash
npx skills add mingdui/ming-qa --list    # 应列出 8 个 skill
```

#### 脚本化安装（CI）

```bash
npx skills add mingdui/ming-qa --agent claude-code --yes \
  -s quality-assurance-agent -s qa-context-profiler -s qa-risk-analyzer \
  -s qa-testcase-designer -s qa-test-script-generator -s qa-test-runner \
  -s qa-code-reviewer -s qa-report-generator
```

`--skill` 一次接一个技能名，装多个就重复写 `-s`。

### 方式二：Claude Code 插件市场

需要 Claude Code CLI。

```
/plugin marketplace add mingdui/ming-qa
/plugin install ming-qa@ming-qa
```

安装后如提示需要重载，执行 `/reload-plugins`。

### 方式三：从源码

适合离线环境，或想自己控制安装位置。

```bash
git clone https://github.com/mingdui/ming-qa.git
cd ming-qa/skills/quality-assurance-agent

./install.sh --target claude-code     # macOS / Linux / Git Bash
.\install.ps1 -Target claude-code     # Windows PowerShell
```

只把 skill 文件复制到目标 skills 目录，不修改 shell 配置或 PATH。
`--target` 也可写 `codex`。

## 用起来

在 agent 里说：

```
使用 quality-assurance-agent，对 <你的模块> 进行验收
```

agent 会自动完成初始化、环境体检和工具链安装，只在需要你配合时停下
（填配置、确认用例）。详见 [README](../README.md)。

## 想自己跑命令

CLI 在 skill 的 `scripts/qa_agent.py`。先解析 skill 目录：

```bash
QA_AGENT_DIR="${QA_AGENT_CLI:-$(dirname "$(find ~/.claude/skills ~/.agents/skills ~/.codex/skills .claude/skills .agents/skills .codex/skills -maxdepth 2 -name SKILL.md -path '*quality-assurance-agent/*' 2>/dev/null | head -1)")}"
```

之后所有命令写成 `python "$QA_AGENT_DIR/scripts/qa_agent.py" <cmd>`：

```bash
# 初始化项目：生成 .qa-agent/ 目录与配置模板
python "$QA_AGENT_DIR/scripts/qa_agent.py" init-project --repo .

# 环境体检
python "$QA_AGENT_DIR/scripts/qa_agent.py" doctor --repo . --strict --check-services
```

`--agent` 可选 `claude-code` / `codex` / `both`。

## 升级

| 安装方式 | 命令 |
|---|---|
| `npx skills`（项目内安装） | `npx skills update` |
| `npx skills`（`-g` 全局） | `npx skills update -g` |
| 插件市场 | `/plugin update ming-qa@ming-qa` |
| 源码 | 重跑安装脚本，加 `--force` / `-Force` |

## 系统要求

- Python 3.9+
- Git
- 目标项目按验收范围需要 Java 21 / Maven 或 Node.js 20+

## 故障排除

| 现象 | 处理 |
|---|---|
| `npx skills` 找不到 skill | 确认仓库根有 `.claude-plugin/marketplace.json` 与 `skills/` 目录；用 `--list` 确认 |
| 插件安装报 SSH 失败 | 市场默认走 SSH 克隆。改用 HTTPS：`/plugin marketplace add https://github.com/mingdui/ming-qa.git` |
| `python` 命令不存在 | 装 Python 3.9+ 并确保在 PATH 中；Windows 上可用 `py -3` |
| `doctor` 输出中文乱码 | Windows 上设置 `PYTHONIOENCODING=utf-8` |

## 卸载

```bash
npx skills remove -g ming-qa                                            # npx skills 装的
/plugin uninstall ming-qa@ming-qa                                       # 插件市场装的
rm -rf ~/.claude/skills/quality-assurance-agent ~/.claude/skills/qa-*   # 源码装的
```
