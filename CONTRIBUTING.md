# 贡献指南

感谢你考虑为本项目做贡献。

## 环境要求

- Python 3.9+
- Git
- （可选）[Claude Code](https://claude.com/claude-code) CLI，用于本地加载插件调试

本工具本身无第三方运行时依赖，只使用 Python 标准库。

## 仓库结构

```
.
├── .claude-plugin/          # Claude Code 插件清单
├── skills/                  # 8 个 skill，npx skills 的发现容器
│   ├── quality-assurance-agent/   # 顶层路由器 + Python CLI
│   └── qa-*/                      # 7 个阶段子 skill
├── docs/                    # 安装、配置、架构文档
└── .github/workflows/       # CI
```

## 本地开发

```bash
git clone https://github.com/mingdui/ming-qa.git
cd ming-qa

# 跑测试（104 个用例）
cd skills/quality-assurance-agent
python -m pytest tests/ -q
```

### 本地加载调试

不需要安装，直接把仓库当插件加载：

```bash
cd ming-qa
claude --plugin-dir .
```

## 提交前自检

CI 会跑以下检查，建议本地先跑一遍：

```bash
cd skills/quality-assurance-agent
python -m py_compile scripts/qa_agent.py
python -m pytest tests/ -q
sh -n install.sh

cd ../..
claude plugin validate .        # 需已安装 Claude Code CLI
```

## 提交规范

- 一个提交只做一件事
- 提交信息用祈使句，首行不超过 72 字符
- 建议前缀：`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`
- 破坏性变更在提交信息正文说明，并同步更新 `CHANGELOG.md`

## 新增一个子 skill

1. 在 `skills/` 下新建目录，命名 `qa-<职责>`，全小写加连字符
2. 创建 `SKILL.md`，YAML frontmatter 必须含 `name` 和 `description`
   - `description` 决定触发准确率，要写清「什么时候用」和「不适用什么场景」
3. 若需要在 Codex 下工作，补 `agents/openai.yaml`
4. 在 `skills/quality-assurance-agent/SKILL.md` 的阶段路由表里登记
5. 在 `skills/quality-assurance-agent/references/stage-skills.md` 补维护规则
6. 在 `docs/architecture.md` 的职责表里补一行

## 修改 CLI 参数时需要同步的文件

`skills/quality-assurance-agent/scripts/qa_agent.py` 是命令语法的唯一真相来源。改动参数后需同步：

- `skills/quality-assurance-agent/references/cli-reference.md` —— 命令语法说明
- `skills/quality-assurance-agent/references/stage-skills.md` 的「Maintenance Rules」章节
- 各子 skill 的 `SKILL.md` 中引用到该参数的段落

完整的维护清单见 `references/stage-skills.md`。

## 报告问题

提交 issue 时请附上：

- 你的 agent（Claude Code / Codex）与版本
- Python 版本与操作系统
- 复现步骤
- `ming-qa doctor --repo . --strict` 的输出（注意先脱敏）

**请勿在 issue 中粘贴真实的账号密码、API Key 或数据库连接串。**
