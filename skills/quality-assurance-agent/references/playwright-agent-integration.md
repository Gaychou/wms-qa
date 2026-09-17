# Playwright Test Agent Integration

当 scope 涉及 E2E 或浏览器自动化时，使用本参考了解 Playwright Test Agent 的安装、路由和复用规则。

官方文档：https://playwright.dev/docs/test-agents

## Claude Code vs Codex 区分

Playwright Test Agent 支持多种 agent 类型，通过 `--loop` 参数区分：

| Agent | 初始化命令 | 生成的 agent 定义位置 |
|---|---|---|
| Claude Code | `npx playwright init-agents --loop=claude` | `.claude/agents/playwright-test-*.md` |
| Codex | `npx playwright init-agents --loop=codex` | `.codex/agents/playwright_test_*.toml` |

**两者的安装步骤、agent 角色（planner/generator/healer）、配置文件内容逻辑完全一致**，唯一区别是生成的定义文件格式适配各自 agent 的 subagent 调用规范。更新 Playwright 版本后需重新运行初始化命令以获取最新的工具和指令。

## 通过 ming-qa 安装

```bash
# Claude Code
ming-qa install-playwright-agents --repo . --loop claude-code --skip-if-present

# Codex
ming-qa install-playwright-agents --repo . --loop codex --skip-if-present
```

也可以在项目初始化时一并安装：

```bash
ming-qa init-project --repo . --install-playwright-agents --loop claude-code
```

### 运行时与浏览器（跑 spec 的硬依赖，与 agents 定义分离）

`install-playwright-agents` 只装 **agents 定义**（planner/generator/healer，用于生成/修复 spec）。真正 `npx playwright test` 跑 spec 还需要 **运行时 + 浏览器**，用单独命令安装：

```bash
# 装 @playwright/test（声明 + node_modules）+ chromium 浏览器二进制（幂等，已就绪则跳过）
ming-qa install-playwright-runtime --repo . --skip-if-present
```

三层就绪模型（doctor 分别检测，不要混为一谈）：

| 层 | doctor 检测项 | 内容 | 用途 |
|---|---|---|---|
| L1 agents 定义 | `playwright_assets` | `.claude/agents/playwright-test-*.md` | 生成/修复 spec |
| L2 运行时 | `playwright_runtime` | `@playwright/test` + `playwright.config` | 跑 spec 硬依赖 |
| L3 浏览器 | `playwright_browsers` | `ms-playwright` 缓存的 chromium 等 | 驱动浏览器 |

`playwright.config` 缺失时由 `install-playwright-runtime` 自动生成默认模板（`testDir: './tests/e2e'`、`baseURL: process.env.QA_WEB_BASE_URL || 'http://127.0.0.1:3000'`、`headless: true`）；如需自定义（多 project、retries、reporter 等）再手动修改。doctor 的 `playwright_config_baseurl` 会校验 config 的 baseURL 与 services 的 `QA_WEB_BASE_URL` 是否一致。

## 已有资产识别

安装完成后，可通过以下特征判断项目中是否存在 Playwright Test Agent：

- **Claude Code**：`.claude/agents/playwright-test-planner.md`、`playwright-test-generator.md`、`playwright-test-healer.md`
- **Codex**：`.codex/agents/playwright_test_planner.toml`、`playwright_test_generator.toml`、`playwright_test_healer.toml`
- **通用**：`specs/`（测试计划目录）、`playwright-report/`（报告目录）、`playwright.config.*`（配置文件）

## Agent 角色路由

Playwright Test Agent 提供三个专职角色，QA 流程按需路由：

1. **Planner（规划器）**：对新的 E2E 界面或跨系统流程，先探索应用并保存 Markdown 测试计划，再写 spec
2. **Generator（生成器）**：将已确认的用例或计划条目转为单个 Playwright spec 文件，保留步骤注释和稳定定位器
3. **Healer（修复器）**：Playwright 测试失败时，先路由到 Healer 修复选择器/时序/数据/环境问题，不要直接削弱断言

QA Agent 始终是编排者——它决定哪些已确认的用例需要走 E2E，调用（或模拟）以上角色，记录证据，在修产品代码前先做失败分类。

## 生成规则

- 一个 spec 文件聚焦一个场景或紧密关联的断言
- 从测试计划复制注释到对应操作前，保持可读性
- 优先使用稳定定位器：role、label、placeholder、已验证的产品文案、稳定的 test-id
- **禁用 `networkidle`**
- 状态变更操作优先用 `waitForResponse` 或等效 API 证据，而非仅检查 UI 变化
- 使用带时间戳的测试数据，避免依赖历史记录数量
- 保留项目已有的认证配置和 storage-state 文件

## 修复规则

- 先跑一遍失败测试，捕获精确错误
- 一次只修一个失败
- 先分类（选择器/时序/测试数据/环境/产品 bug），再决定是否修改
- 测试断言本身正确时只修测试，不削弱断言
- 测试有效但产品有 bug：把失败交给 QA 修复循环，不削弱断言绕过
- `test.fixme()` 仅用于确实无法可靠执行的情况，并在附近注释说明阻塞原因

## 已有资产复用

创建 E2E 测试前：

1. 如果项目需要 E2E 生成/修复但缺少 Playwright Test Agent，自动安装
2. 读取 `.claude/agents/playwright-test-*.md` 或 `.codex/agents/playwright_test_*.toml`
3. 读取 `playwright.config.*` 确认 testDir、认证配置、base URL、viewport、retries、reporters
4. 读取已有 `specs/**/*.plan.md` 和相邻 `*.spec.ts`
5. 沿用项目已有目录约定（`specs/auth`、`specs/admin`、`specs/cross-system` 等）
6. 诊断当前失败时查阅 `playwright-report/index.html` 和 test-result 产物

## 证据记录

每次 E2E 执行记录：

- 命令：如 `npm run test:local`、`npm run test:admin:local`
- 使用的配置文件
- Base URL 和环境变量（不含密钥）
- 项目本地报告路径：`playwright-report/<scope>/index.html`
- QA 报告路径：`.qa-agent/reports/<scope>/<run-id>/`
- 如有 trace/screenshot/video，记录路径
- 失败的 test title、文件、行号、错误摘要

## 产物布局

遵循 QA Agent 产物约定：

- 原始执行证据：`.qa-agent/runs/<run-id>/playwright/<scope>/`
- 范围报告包：`.qa-agent/reports/<scope>/<run-id>/`
- 最新指针：`.qa-agent/reports/<scope>/latest-report.html`

不同 scope 的报告不混在同一目录。
