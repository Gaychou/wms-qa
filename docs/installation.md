# 安装

本工具以 **Agent Skill** 形式分发。装好之后由 agent 驱动，不需要自己敲命令。

## 安装方式

### 方式一：`npx skills`（推荐）

```bash
npx -y skills add mingdui/ming-qa -g -y
```

适用于 Claude Code、Codex、Cursor 等 40 多种 agent——技能装到通用的
`~/.agents/skills/`，再链接进本机所有已检测到的 agent。

`-y` 一次装全 8 个技能。不带它会进入交互选择，逐个挑比较麻烦。

开头那个 `npx -y` 是跳过 npx 自己的「是否安装 skills 包」询问——**两个 `-y` 作用不同**，
只有 `skills` 后面的 `-y` 压不住 npx 的提问。少了前者，第一次安装会停在
`Ok to proceed? (y)` 上；脚本和 CI 里则直接挂住。

`-g` 装到用户级目录，对所有项目生效；省略 `-g` 则装到当前项目。

默认用**符号链接**把技能链接进各 agent 的目录（单一事实来源，更新一次全部生效），
想改用复制加 `--copy`。

验证：

```bash
npx -y skills add mingdui/ming-qa --list    # 应列出 8 个 skill
```

#### 脚本化安装（CI）

```bash
npx -y skills@1.7.0 add mingdui/ming-qa --agent claude-code --yes \
  -s quality-assurance-agent -s qa-context-profiler -s qa-risk-analyzer \
  -s qa-testcase-designer -s qa-test-script-generator -s qa-test-runner \
  -s qa-code-reviewer -s qa-report-generator
```

`--skill` 一次接一个技能名，装多个就重复写 `-s`。

CI 里把 `skills` 锁到具体版本（上面的 `@1.7.0`），避免 CLI 升级在你不察觉时改变行为；
升级时手动改这个版本号。日常交互式安装不必锁。

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

## 安装输出的安全评级

`npx skills` 装完会打印一张第三方评级表（Gen / Socket / Snyk）。它评估的是能力面，
不是「是否恶意」——本工具会执行测试、改动产品代码、连接数据库，被标记是这类工具的
常态。评级随重扫变化，以页面为准：<https://skills.sh/mingdui/ming-qa>

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
| `npx skills`（项目内安装） | `npx -y skills update` |
| `npx skills`（`-g` 全局） | `npx -y skills update -g` |
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
| `doctor` 报某个必须项，但本项目用不到 | 用 `--ignore <检查名>` 逐项豁免（检查名会在输出里列出）。被豁免的项仍会显示，只是不再阻塞。agent 遇到这情况也会提示你 |
| 装完末尾出现 `Failed to install N` | 看原因：若是某个 agent「不支持全局安装」（如 PromptScript），那是该 agent 自己的限制，安装其实成功了。想避免出现，用 `--agent claude-code` 只装指定 agent |
| `.mcp.json` / `.mysql-mcp/credentials` 含明文数据库密码 | 用 `--install-mysql-mcp` 时会写入，确认这两项在 `.gitignore` 里（`init-layout --root-gitignore` 的推荐片段只覆盖 `.qa-agent/`，需自己补）。若已提交过，删除文件不够，需更换密码 |

## 卸载

```bash
npx -y skills remove -g ming-qa                                         # npx skills 装的
/plugin uninstall ming-qa@ming-qa                                       # 插件市场装的
rm -rf ~/.claude/skills/quality-assurance-agent ~/.claude/skills/qa-*   # 源码装的
```
