# 架构

## 组成

本工具由 1 个顶层路由器 + 7 个阶段子 skill + 1 个 Python CLI 构成。

| # | Skill | 职责 | 是否判断质量 |
|---|---|---|---|
| 0 | `quality-assurance-agent` | 路由器。按阶段调用子 skill，自己不写测试、不判质量 | — |
| 1 | `qa-context-profiler` | 收集仓库事实与环境证据，不做任何判断 | 否 |
| 2 | `qa-risk-analyzer` | 识别高风险业务路径与必需验证点 | 否 |
| 3 | `qa-testcase-designer` | 生成中文业务用例，等待用户确认 | 否 |
| 4 | `qa-test-script-generator` | 把已确认用例转成 spec-task 与测试脚本 | 否 |
| 5 | `qa-test-runner` | 执行、分类失败、修最小根因、跑 completion 门禁 | 否 |
| 6 | `qa-code-reviewer` | 独立视角代码审查，产出 `code-review.json` | 是 |
| 7 | `qa-report-generator` | 汇总三门禁产物，渲染报告，最终就绪判定 | 是 |

**只有阶段 6、7 判断质量。** 前五个阶段只负责收集、转换、执行，避免「自己判自己合格」。

## 执行链路

```
阶段 0 上下文收集
   ↓
阶段 1 风险分析
   ↓
阶段 2 用例设计  ←── 唯一强制人工门禁：等你确认用例
   ↓
阶段 3 脚本生成
   ↓
阶段 4 执行与修复（自动）
   ↓
阶段 5 代码审查（自动）
   ↓
阶段 6 报告与最终判定（自动）
```

用例确认之后的所有阶段自动衔接，中间不需要人工介入。

## 三个门禁

每一步切换前必须确认上游产物存在，产物缺失不允许跳过门禁。

| 门禁 | 产物 | 作用 |
|---|---|---|
| completion | `completion-check.json` | 所有 task 是否执行完并通过 |
| code-review | `code-review-check.json` | 是否存在 P0/P1 blocking 发现 |
| readiness | `readiness-check.json` | 汇总前两者，给出最终判定 |

最终就绪语言分四档：**就绪 / 有条件就绪 / 未就绪 / 未完成**。

注意：completion 通过但 code-review 有 P1 blocking 时，判定为未就绪——
不因为「用例都跑通了」就说 Ready。

## CLI 调用约定

`skills/quality-assurance-agent/scripts/qa_agent.py` 是命令语法的唯一真相来源。

它**不作为 PATH 上的命令分发**——命令由 agent 执行，人不需要手敲。
先解析一次 skill 目录，之后所有命令写成 `python "$QA_AGENT_DIR/scripts/qa_agent.py" <cmd>`：

```bash
QA_AGENT_DIR="${QA_AGENT_CLI:-$(dirname "$(find ~/.claude/skills ~/.agents/skills ~/.codex/skills .claude/skills .agents/skills .codex/skills -maxdepth 2 -name SKILL.md -path '*quality-assurance-agent/*' 2>/dev/null | head -1)")}"
```

运行环境若已告知 skill 目录（Claude Code 会），直接用，不必跑上面的查找。
`$QA_AGENT_CLI` 优先级最高，供团队显式指定路径。

这个约定让同一套文档在三种安装形态下都成立（`npx skills` 安装、
插件市场安装、源码安装脚本），不需要为每种安装方式维护一套命令行写法。

## 产物目录

运行产物都在目标项目的 `.qa-agent/` 下。

| 目录 | 内容 | git clone 后 |
|---|---|---|
| `cases/` | 已确认的长期用例 | ✅ |
| `spec-tasks/` | spec-task 蓝图（用例→脚本映射） | ✅ |
| `config/` | 项目 QA 配置 | ✅ |
| `profiles/` | 项目测试 profile | ✅ |
| `risk-rules/` | 风险规则 | ✅ |
| `fixtures/` | 账号/服务示例模板（脱敏后） | ✅ |
| `knowledge/` | 项目经验库 | ✅ |
| `reports/` | HTML 报告 | ✅ |
| `current/` | 本轮运行产物 | ❌ 需重新生成 |
| `runs/` | 执行日志与证据 | ❌ |
| `local/` | 本地账号密码 | ❌ |

**git clone 后首次回归**：`current/` 丢失是正常的。先跑 `init-project` 建目录，
再用 `generate-spec-tasks --acceptance-mode` 从 `cases/` 重新生成
`test-spec-tasks.json`。测试脚本在 `tests/api/` 下，不受影响。

## 数据流向

```
仓库代码 ─→ qa-context-profiler ─→ context.json
                                        ↓
用户需求 ─→ qa-risk-analyzer ────→ risk-analysis.json
                                        ↓
                              qa-testcase-designer
                                        ↓
                              test-cases.json  ←── 你在这里确认
                                        ↓
                           qa-test-script-generator
                                        ↓
                              test-spec-tasks.json
                                        ↓
                                qa-test-runner
                                        ↓
                    test-results + evidence + completion-check.json
                                        ↓
                               qa-code-reviewer
                                        ↓
                                 code-review.json
                                        ↓
                              qa-report-generator
                                        ↓
                    latest-report.html + readiness-check.json
```

## 外部依赖与降级

| 依赖 | 用途 | 不可用时的行为 |
|---|---|---|
| Playwright 运行时 | 前端 E2E | 记录到 `environment-checks.json`，纯 API 验收可不需要 |
| MySQL MCP | 数据库资金/状态校验 | 降级为 API 替代验证，在 evidence 中标注信息损失 |
| LLM 网关 | 多模型交叉审查 | 跳过该阶段，写「全部模型失败」结果，不中断流程 |
| webhook | 报告告警 | 未配置则完全不发；发送失败只写 stderr，不阻断 |

**本工具不内置任何默认外部服务地址。** 所有外部地址都必须由用户显式配置，
未配置时不发起任何网络请求。

## 目录布局为什么是 `skills/`

8 个 skill 必须位于 `skills/` 这类容器目录下，`npx skills` 才能发现它们——
该 CLI 扫描固定的容器目录名并向下走 3 层，仓库根目录只有直接含 `SKILL.md` 时才被接受。

因此仓库根 = 插件根，`skills/` 下平铺 8 个 skill 目录。
