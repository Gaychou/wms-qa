# 安装

本工具以 **Agent Skill** 形式分发，不是传统的库或服务。三种安装方式按推荐顺序排列。

## 方式一：`npx skills`（推荐）

适用于 Claude Code、Codex、Cursor 等 40 多种 agent，跨工具通用。

```bash
npx skills add mingdui/ming-qa -g
```

`-g` 表示安装到用户级目录（`~/.claude/skills/`），对所有项目生效。省略 `-g` 则装到当前项目。

安装时 CLI 会让你选择 **Symlink**（推荐，单一事实来源，便于更新）或 **Copy**。

### 非交互安装（脚本化 / CI）

```bash
npx skills add mingdui/ming-qa --agent claude-code --yes \
  -s quality-assurance-agent -s qa-context-profiler -s qa-risk-analyzer \
  -s qa-testcase-designer -s qa-test-script-generator -s qa-test-runner \
  -s qa-code-reviewer -s qa-report-generator
```

两个容易踩的点：

- **`--agent` 的取值是 `claude-code`，不是 `claude`。** 传 `claude` 会直接报
  `Invalid agents: claude` 并中止，不会安装任何东西。
- **`--skill` 只接受单个精确名称。** 不支持逗号分隔，也不支持 `*` 这类通配符——
  CLI 会把 `*` 当成**文件系统**通配符在你当前目录展开，于是报出
  `No matching skills found for: AGENTS.md, README.md, src, …` 这种看似不相干的错误。
  要装多个就重复写 `-s`；想装全部则省略 `--skill` 走交互式选择，或用 `--all`
  （注意 `--all` 同时会把 agent 也设成 `*`，会写入本机所有 agent 的配置目录）。

验证：

```bash
npx skills add mingdui/ming-qa --list      # 应列出 8 个 skill
npx skills ls -a claude-code
```

升级：

```bash
# 在项目里（skills-lock.json 记录了来源）：更新本项目的全部 skill
npx skills update

# 全局安装的（仅对通过 npx skills add -g 装的有效）：
npx skills update -g
```

> 注意不要写 `npx skills update ming-qa`。`ming-qa` 是**仓库名**，不是 skill 名——
> 装进去的 8 个 skill 叫 `quality-assurance-agent` / `qa-*`。按仓库名更新会得到
> `No installed skills found matching: ming-qa`。
>
> 用**源码安装脚本**（方式三）装的没有登记进 skills-lock，`npx skills` 找不到它，
> 升级方式是重跑安装脚本加 `--force` / `-Force`。

## 方式二：Claude Code 官方插件市场

需要 Claude Code CLI。

```
/plugin marketplace add mingdui/ming-qa
/plugin install ming-qa@ming-qa
```

升级：

```
/plugin update ming-qa@ming-qa
```

安装后如提示需要重载，执行 `/reload-plugins`。

## 方式三：从源码安装脚本

适合离线环境或想自己控制安装位置。

```bash
git clone https://github.com/mingdui/ming-qa.git
cd ming-qa/skills/quality-assurance-agent

./install.sh --target claude-code     # macOS / Linux / Git Bash
.\install.ps1 -Target claude-code     # Windows PowerShell
```

脚本**只把 skill 文件复制到目标 skills 目录**，不会修改你的 `~/.bashrc`、
`~/.zshrc`、`~/.bash_profile` 或用户 PATH。它会在 skill 目录下生成 `bin/` shim，
如果你想要终端里能直接敲 `ming-qa`，把这个 `bin/` 目录自行加进 PATH 即可。

## 安装后

### 1. 初始化项目

CLI 由 skill 内的脚本提供。装了 pipx 之外的任何方式，都通过脚本路径调用：

```bash
# macOS / Linux / Git Bash
python ~/.claude/skills/quality-assurance-agent/scripts/qa_agent.py init-project --repo . --agent claude-code

# Windows PowerShell
python "$env:USERPROFILE\.claude\skills\quality-assurance-agent\scripts\qa_agent.py" init-project --repo . --agent claude-code
```

`--agent` 可选 `claude-code` / `codex` / `both`（旧名 `claude` 仍兼容）。

> 若已把 skill 的 `bin/` 加进 PATH，或自行做了别名，可直接用 `ming-qa init-project ...`。
> 下文为简洁一律写 `ming-qa <cmd>`，按上面的路径替换即可。

一条命令生成 `.qa-agent/` 目录结构、配置模板，并装好 E2E 环境
（Playwright Test Agents 定义 + `@playwright/test` + `playwright.config` + 浏览器二进制）。

### 2. 填配置

`init-project` 已生成全部配置模板。你只需编辑本地密钥文件：

**`.qa-agent/local/.env`** —— API Key、测试账号密码等。此文件已 git-ignored，**不要提交**。

其余共享配置在 `.qa-agent/config/` 下，随项目 git 分发。

### 3. 环境体检

```bash
ming-qa doctor --repo . --strict --check-services
```

按提示修复必须项。

### 4. 开始验收

在 Claude Code / Codex 中说：

```
使用 quality-assurance-agent，对 <你的模块> 进行验收
```

## 系统要求

- Python 3.9+
- Git
- 目标项目按验收范围需要 Java 21 / Maven 或 Node.js 20+

## 故障排除

| 现象 | 原因与处理 |
|---|---|
| `npx skills` 找不到 skill | 确认仓库根有 `.claude-plugin/marketplace.json` 与 `skills/` 目录；用 `--list` 确认 |
| 插件安装报 SSH 失败 | 市场通过 SSH 克隆。改用完整 HTTPS URL：`/plugin marketplace add https://github.com/mingdui/ming-qa.git` |
| `python` 命令不存在 | 装 Python 3.9+ 并确保在 PATH 中；Windows 上可用 `py -3` |
| skill 装上了但触发不了 | 检查 `SKILL.md` 的 frontmatter 是否同时有 `name` 和 `description` |
| `doctor` 报中文乱码 | Windows 上设置 `PYTHONIOENCODING=utf-8` |

## 卸载

```bash
npx skills remove -g ming-qa
# 或
/plugin uninstall ming-qa@ming-qa
# 从源码装的：删掉对应的 skills 子目录即可
```
