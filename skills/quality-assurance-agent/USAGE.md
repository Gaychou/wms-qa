# Quality Assurance Agent 详细使用说明

`quality-assurance-agent` 是一个可移植的 QA skill 包，面向 Windows / macOS / Linux 和不同项目复用。它把 QA 流程拆成固定阶段：初始化、上下文采集、风险分析、用例确认、spec-task 拆解、自动执行、失败修复、报告收口、代码审查。

核心原则：

- 报告只读当前门禁产物，不手写结论。
- 业务用例确认是唯一人工门禁。
- `draft` 和 `confirmed` 必须分离。
- 所有产物都落在固定目录，能追踪、能复跑、能审计。

## 1. 安装与启动

### 推荐安装方式

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1 -AddUserPath
```

macOS / Linux：

```bash
bash install.sh --add-user-path
```

可选参数：

- `--skills-path <path>`：安装到自定义 skills 目录。
- `--force`：覆盖已安装版本。
- `--add-user-path`：把 launcher 加入用户 PATH。

### 启动方式

安装后直接这样用：

```bash
ming-qa init-project --repo .
ming-qa doctor --repo . --strict --check-services
```

如果你正在技能源码目录里直接调试，也可以用：

```bash
python scripts/qa_agent.py <command> ...
```

Windows 下 `install.ps1` 会同时准备可执行 launcher；macOS / Linux 下 `install.sh` 会准备可执行 shell launcher。

## 2. 第一次接入新项目

先在目标仓库根目录执行初始化：

```bash
ming-qa init-project --repo .
```

这一步会生成 `.qa-agent/` 目录结构、配置文件模板，并默认装好 E2E 环境（Playwright Test Agents 定义 + `@playwright/test` + `playwright.config` + 浏览器二进制）。生成并整理：

- `.qa-agent/config/`
- `.qa-agent/cases/`
- `.qa-agent/profiles/`
- `.qa-agent/risk-rules/`
- `.qa-agent/fixtures/`
- `.qa-agent/local/`
- `.qa-agent/current/`
- `.qa-agent/runs/`
- `.qa-agent/reports/`

然后只填写本地文件：

```text
.qa-agent/local/.env
```

接着做严格环境预检：

```bash
ming-qa doctor --repo . --strict --check-services
```

`doctor` 会检查：

- 本地环境变量是否齐全。
- 服务地址是否可达。
- Playwright / MySQL MCP 等可选能力是否需要补齐。
- 编码与运行环境是否存在明显问题。

如需初始化后立即验证数据库连通性，可加 `--verify-mysql-mcp`：

```bash
ming-qa init-project --repo . --verify-mysql-mcp
```

## 3. 用户只需要记住的 3 条

### 1) 安装 + 初始化 + 预检

新项目先执行：

```bash
ming-qa init-project --repo .
ming-qa doctor --repo . --strict --check-services
```

如需初始化后立即验证数据库连通性，可加 `--verify-mysql-mcp`：

```bash
ming-qa init-project --repo . --verify-mysql-mcp
```

### 2) 执行 QA

日常验收直接说：

```text
使用 quality-assurance-agent，验收当前改动
```

这会自动完成：上下文采集、风险分析、用例确认、spec-task 拆解、自动执行、失败修复、报告收口、代码审查。

### 3) 历史测试用例手动回归

当你只想复跑已确认的历史用例时，直接说：

```text
使用 quality-assurance-agent，基于已确认的历史用例做回归
```

这条适合老需求重跑、回归检查、或只想确认既有 case 是否仍然成立的场景。

## 4. Playwright Test Agent 约定

当项目有 E2E，尤其是新页面、跨系统流、H5 -> Admin -> H5 流程时，优先遵守这条顺序：

1. Planner：先产出测试计划。
2. Generator：把确认后的场景变成单个 spec 文件。
3. Healer：失败时先修 selector、等待、数据和环境，再考虑放宽断言。
4. 稳定重跑：只做干净重跑或报告刷新时，可以跳过 Planner / Generator / Healer。

相关资产和落位规范见主 skill SKILL.md 的「产物目录约定」章节，以及：

- `references/playwright-agent-integration.md`

## 5. 产物目录约定

长期知识（Git 跟踪）：

- `.qa-agent/config/`
- `.qa-agent/cases/`
- `.qa-agent/profiles/`
- `.qa-agent/risk-rules/`
- `.qa-agent/fixtures/`
- `.qa-agent/reports/`（验收报告需要留痕、可追溯，纳入 Git 跟踪）

运行态（Git 忽略）：

- `.qa-agent/local/`
- `.qa-agent/current/`
- `.qa-agent/runs/`
- `.qa-agent/archive/`
- `.qa-agent/cache/`
- `.qa-agent/tmp/`

规则：

- 不要把运行产物散在项目根目录。
- 报告、门禁、证据、任务必须来自同一轮运行。
- 报告更新后要重新做 freshness 检查。

## 6. 高级手动触发

下面这些是给高级用户和复跑场景准备的，日常不需要记：

### 只跑某个门禁

```bash
ming-qa run-commands --repo . --config .qa-agent/config/qa-agent.config.yaml --gate e2e
```

可用 gate：

- `unit`
- `api`
- `integration`
- `e2e`
- `review`

### 只跑某个范围

把过滤条件写进对应 gate 的命令里，再执行同一个 gate。

### 只跑 E2E

```bash
ming-qa run-loop --repo . --config .qa-agent/config/qa-agent.config.yaml --gates e2e --output .qa-agent/runs/latest-run.json
```

## 7. 新增工具命令

### run-with-env：统一测试脚本执行入口

替代手动 `env $(sed...) bash` 的繁琐流程，自动加载 `.qa-agent/local/.env`、处理 CRLF 换行、传递变量到子进程、记录执行日志：

```bash
ming-qa run-with-env --repo . --script tests/api/order/tc-p0-001-create-single.sh
ming-qa run-with-env --repo . --script tests/api/order/tc-p0-001-create-single.sh --extra "TARGET_BOX_ID=5"
ming-qa run-with-env --repo . --script tests/api/order/tc-p0-001.sh --dry-run   # 仅打印命令不执行
```

日志自动写入 `.qa-agent/runs/run-<script-name>-<timestamp>.log`。

### atomic-commit：repair 动作路径白名单/黑名单

`atomic-commit` 在真正 `git add` 之前，会读取 `qa-agent.config.yaml` 里的 `repair.allowedPaths` / `repair.deniedPaths`，校验本次要提交的路径：

```yaml
repair:
  allowedPaths: []          # 为空表示不限制业务代码路径
  deniedPaths:
    - ".qa-agent/**"
    - ".github/**"
```

规则：`deniedPaths` 始终优先生效；若 `allowedPaths` 非空，路径必须命中其中至少一条。任一路径被拒绝时，命令直接报错退出，**不会执行任何 `git add`**（fail-closed，不做部分提交）。默认示例配置只拦截 `.qa-agent/**` 和 `.github/**`，避免修复动作误改产物目录或 CI 配置。

### manifest：子 skill 间结构化数据传递

各阶段命令执行后自动更新 `.qa-agent/current/manifest.json`，下游 skill 可直接读取上游产物路径和阶段状态，消除自然语言 args 手工传递的信息衰减：

```bash
ming-qa manifest --repo .   # 查看当前 manifest（产物路径、阶段状态）
```

manifest.json 结构：

```json
{
  "currentStage": "test-runner",
  "artifacts": {
    "risk-analysis": ".qa-agent/current/risk-analysis.json",
    "spec-tasks": ".qa-agent/current/test-spec-tasks.json",
    "confirmed-cases": ".qa-agent/cases/xxx.json",
    "run-loop": ".qa-agent/runs/latest-run.json",
    "cases": ".qa-agent/cases/xxx.json",
    "code-review": ".qa-agent/current/code-review.json"
  },
  "status": {
    "risksAnalyzed": "done",
    "specTasksGenerated": "done",
    "casesConfirmed": "done",
    "loopIteration": 1,
    "loopStatus": "passed",
    "maxRepairLoops": 5,
    "resultsUpdated": "done",
    "codeReviewed": "passed"
  }
}
```

manifest 现在覆盖用例确认（`promote-cases`）、执行循环（`run-loop`）、结果回写（`update-results`）、代码评审（`assert-code-review`）四个阶段，中断后可以直接读 manifest 判断跑到了哪一步、要不要继续跑循环（看 `loopIteration`/`loopStatus`/`maxRepairLoops`）。

下游 AI skill 中只需 `Read .qa-agent/current/manifest.json` 即可获取上游所有产物路径，无需从自然语言参数中重新描述。

### safe-write-json：安全写入中文 JSON

规避 AI Write/Edit 工具在 Windows 上的中文编码损坏（U+FFFD）风险：

```bash
python3 -c "import json,sys; sys.stdout.write(json.dumps(data, ensure_ascii=False))" | ming-qa safe-write-json .qa-agent/current/output.json --from-stdin
```

## 8. 常见故障与解决方案

### AI 工具写入中文 JSON 偶发 U+FFFD 编码损坏

**现象**：`risk-analysis.json`、`test-cases.json` 等产物中出现 U+FFFD 替换字符（Unicode REPLACEMENT CHARACTER），导致 `validate-cases --check-mojibake` 或 `render-report` 失败。

**根因**：AI 的 Write/Edit 工具在 Windows 上处理多字节中文时偶发部分字节损坏，被替换为 U+FFFD。

**规避方案（推荐）**：不通过 AI Write/Edit 工具直接写中文 JSON 文件内容，改用 `ming-qa safe-write-json`，通过 Python 管道传递 JSON 内容：

```powershell
# ❌ 避免：让 AI 用 Write 工具直接写大段中文 JSON
# ✅ 改用：让 AI 用 Python 管道传递 JSON 给 safe-write-json
python3 -c “
import json, sys
#  在此构造 JSON 数据
data = {'test': '中文测试', 'ok': True}
sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2))
“ | ming-qa safe-write-json .qa-agent/current/your-file.json --from-stdin
```

`safe-write-json` 会在写文件后立即做 JSON 合法性校验 + U+FFFD 扫描，确保写入内容无编码损坏。优先使用 `--from-stdin`（管道输入），备选 `--json-string`。

**验证命令**：

```powershell
ming-qa check-mojibake .qa-agent/current/*.json --strict
```

### Maven 在 Git Bash 下 classpath argfile 写入 C:\Windows 失败

**现象**：`mvn spring-boot:run` 报 `Could not build classpath: C:\Windows\spring-boot-....argfile`。

**根因**：Git Bash 子进程的 `java.io.tmpdir` 继承了系统级 `TMP` 环境变量（`C:\Windows\TEMP`），普通用户对该目录无写权限。

**解决方案**：通过 PowerShell 原生进程启动（不受 Git Bash 环境变量污染）：

```powershell
Start-Process -FilePath “mvn.cmd” -ArgumentList “spring-boot:run” -RedirectStandardOutput “backend.out.log” -RedirectStandardError “backend.err.log” -WindowStyle Hidden
```

### generate-spec-tasks 默认最小任务数对验收场景不适用

**现象**：执行 `generate-spec-tasks` 后，每条 P0 用例被拆成 8 个 unit+integration+api+e2e 任务（共 40+ 任务），但验收场景只需每条用例 1 个 api 层任务。

**解决**：使用 `--acceptance-mode`：

```powershell
ming-qa generate-spec-tasks --cases .qa-agent/current/test-cases.json --repo . --output .qa-agent/current/test-spec-tasks.json --acceptance-mode
```

等价于 `--min-specs-by-priority P0=1,P1=1,P2=1,P3=1 --ratio unit=0,integration=0,api=1,e2e=0`。

## 9. 可移植性说明

这个 skill 的设计目标是”拷贝到新机器、新项目也能继续跑”：

- 命令入口固定为 `ming-qa`。
- 目录边界固定为 `.qa-agent/`。
- 业务确认、spec-task、执行结果、报告和复核都有独立产物。
- Windows 和 macOS / Linux 只差安装脚本，不差工作流。

如果你发现某个路径还写死成了个人机器路径，优先改成 launcher、相对路径或 `ming-qa` 命令。
