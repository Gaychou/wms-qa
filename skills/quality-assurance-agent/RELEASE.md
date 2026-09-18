# QA Agent 发版指南

本文档描述如何发布新版本，以及用户如何升级。

## 分发架构

- **唯一代码源**：GitHub 仓库 [mingdui/ming-qa](https://github.com/mingdui/ming-qa)。
- **渠道一（推荐）**：`npx skills add mingdui/ming-qa -g`
- **渠道二**：Claude Code 官方插件市场 `/plugin marketplace add mingdui/ming-qa`
- **渠道三**：从源码运行 `install.sh` / `install.ps1`（离线环境 / 自定义安装位置）

本工具**没有自更新机制**。用户通过上述渠道自带的更新能力升级：

```bash
# npx skills 渠道：按项目更新（技能名不是仓库名，传 ming-qa 会找不到）
npx skills update
# 或
/plugin update ming-qa@ming-qa
```

> 源码安装（方式三）没有登记进 skills-lock，`npx skills` 更新不到，需重跑
> `install.sh --force` / `install.ps1 -Force`。

## 发布前自检

```bash
cd skills/quality-assurance-agent
python -m py_compile scripts/qa_agent.py      # 语法自检
python -m pytest tests/ -q                    # 应全绿
python scripts/qa_agent.py --version          # 确认版本号
sh -n install.sh                              # shell 脚本语法自检

cd ../..
claude plugin validate .                      # 插件清单校验
```

## 发版 checklist

### 1. 改版本号（两处必须一致）

| 文件 | 字段 |
|---|---|
| `skills/quality-assurance-agent/scripts/qa_agent.py` | `SKILL_VERSION` |
| `.claude-plugin/plugin.json` | `version` |

版本号不一致会导致插件市场不推送更新。

### 2. 更新 CHANGELOG.md

按 [Keep a Changelog](https://keepachangelog.com/) 格式记录本次变更，破坏性变更必须显式标注。

### 3. 跑自检

见上一节，全部通过再继续。

### 4. 打标签与发布

```bash
git tag v2.0.0
git push origin main --tags
gh release create v2.0.0 --generate-notes
```

### 5. 验证安装渠道

```bash
npx skills add mingdui/ming-qa --list          # 应列出 8 个 skill
claude plugin validate .                        # 应通过
python skills/quality-assurance-agent/scripts/qa_agent.py --version   # 应输出 SKILL_VERSION
```

## 版本号约定

- 语义化版本：`major.minor.patch`
- 破坏性变更（如删除子命令）递增 major，并在 CHANGELOG 的 `### Removed` 段落明确写出
- 首次公开发布为 `2.0.0`（与内部时代的 1.1.x 区分）
