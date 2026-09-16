# CLI 命令参考（唯一真相来源，子 skill 依赖这里）

本节是完整的命令语法参考。子 skill 不再各自维护命令章节，而是通过引用"主 skill CLI 命令参考"获取语法。

## 通用工具（所有阶段可用）

```powershell
# 查看当前 QA 流程 manifest（产物路径和阶段完成状态）
ming-qa manifest --repo .

# 加载 .qa-agent/local/.env 并执行测试脚本（自动处理 CRLF/变量传递/日志）
ming-qa run-with-env --repo . --script <脚本相对路径> [--extra KEY=VAL]...

# 在 playwrightDir（默认 tests/）执行 Playwright spec，并写 run 证据（log+sidecar，供 aggregate-runs 自动聚合）
ming-qa run-e2e --repo . --spec tests/e2e/<module>/<case-id>.spec.ts [--extra KEY=VAL]...

# 安全写入 JSON 文件（规避 Windows Write 工具的中文 U+FFFD 编码损坏）
python3 -c "..." | ming-qa safe-write-json <目标路径> --from-stdin

# 编码完整性检查
ming-qa check-mojibake <文件路径...> --strict
```

## 前置准备：布局与环境

```powershell
ming-qa init-project --repo .
ming-qa doctor --repo . --strict --check-services --json .qa-agent/current/environment-checks.json
```

> Playwright 运行时（`@playwright/test` + `playwright.config.js` + 浏览器）统一落盘到
> `qa-agent.config.yaml` 的 `playwright.dir`（默认 `tests/`），避免根目录 lockfile 干扰前端
> Next.js workspace root 推断（导致动态路由 404）。`install-playwright-runtime` 自动装到该目录，
> `run-e2e` 在该目录执行 spec。`playwright.config.js` 的 `testDir` 为 `./e2e`（相对 playwrightDir）。

## 阶段 0：上下文

```powershell
ming-qa collect-context --repo . --scope uncommitted --output .qa-agent/current/context.json
ming-qa index-existing-cases --repo . --output .qa-agent/current/existing-case-index.json
```

## 阶段 1：风险分析

```powershell
# 验收场景（推荐）：限定到具体模块文件，避免全仓库关键词扫描污染 affectedFiles
ming-qa analyze-risks --repo . \
  --context .qa-agent/current/context.json \
  --existing-index .qa-agent/current/existing-case-index.json \
  --module "src/main/java/.../OpenBoxServiceImpl.java,src/main/java/.../OpenBoxController.java" \
  --output .qa-agent/current/risk-analysis.json

# 开发场景（无 git diff 时回退到全仓库扫描）
ming-qa analyze-risks --repo . --context ... --existing-index ... --output ...
```

`--module` 接受逗号分隔的文件路径、目录路径或 glob 表达式。验收场景中不带此参数将导致 `affectedFiles` 混杂全仓库无关文件。

## 阶段 2：用例设计

```powershell
ming-qa merge-existing-cases --repo . --generated .qa-agent/current/test-cases.generated.json --existing-index .qa-agent/current/existing-case-index.json --output .qa-agent/current/test-cases.json
ming-qa validate-cases --cases .qa-agent/current/test-cases.json --summary --check-mojibake --strict-language
ming-qa render-cases --cases .qa-agent/current/test-cases.json --output .qa-agent/current/test-cases.html
ming-qa review-cases --cases .qa-agent/current/test-cases.json --context .qa-agent/current/context.json --output .qa-agent/current/model-review.json
ming-qa check-mojibake .qa-agent/current/test-cases.json .qa-agent/current/test-cases.html .qa-agent/current/model-review.json --strict
# 用户确认后：
ming-qa promote-cases --cases .qa-agent/current/test-cases.json --repo . --module <模块名>
```

## 阶段 3：脚本生成

```powershell
# 完整测试金字塔（默认）：每条用例按 unit/integration/api/e2e 逐级递减拆解
ming-qa generate-spec-tasks --cases .qa-agent/current/test-cases.json --repo . --output .qa-agent/current/test-spec-tasks.json

ming-qa coverage-balance --spec-tasks .qa-agent/current/test-spec-tasks.json --output .qa-agent/current/coverage-balance.json --strict

ming-qa assert-oracle-mapping --risk-analysis .qa-agent/current/risk-analysis.json --spec-tasks .qa-agent/current/test-spec-tasks.json
```

默认最小 task 数 P0=8/P1=5/P2=3/P3=1、比例 unit 60%/integration 20%/api 15%/e2e 5%。`--acceptance-mode` 是「仅 api 层」的遗留选项（等价 `--ratio unit=0,integration=0,api=1,e2e=0`），不再作为默认使用。

`coverage-balance` 的 `--ratio` / `--min-specs-by-priority` 默认读 spec-tasks 根级的 `targetRatio` / `minSpecsByPriority`，无需手动传等价参数。

`assert-oracle-mapping` 校验每条 P0/P1 风险的 requiredAssertions 都映射到某个 spec-task 的 oracle/assertions。

## 阶段 4：执行与修复

```powershell
ming-qa run-loop --repo . --config .qa-agent/config/qa-agent.config.yaml --output .qa-agent/runs/latest-run.json
ming-qa update-results --cases .qa-agent/current/test-cases.json --run .qa-agent/runs/latest-run.json
ming-qa assert-completion --cases .qa-agent/current/test-cases.json --spec-tasks .qa-agent/current/test-spec-tasks.json --priorities P0,P1,P2 --min-specs-by-priority P0=1,P1=1,P2=1 --output .qa-agent/current/completion-check.json
```

## 阶段 5：代码审查

```powershell
ming-qa assert-code-review --code-review .qa-agent/current/code-review.json --output .qa-agent/current/code-review-check.json
```

## 阶段 6：报告生成

```powershell
ming-qa aggregate-runs --repo . --output .qa-agent/current/latest-run.json
ming-qa assert-evidence-integrity --cases .qa-agent/current/test-cases.json --spec-tasks .qa-agent/current/test-spec-tasks.json --run .qa-agent/current/latest-run.json --code-review .qa-agent/current/code-review.json --output .qa-agent/current/evidence-integrity-check.json
ming-qa render-report --cases .qa-agent/current/test-cases.json --run .qa-agent/current/latest-run.json --spec-tasks .qa-agent/current/test-spec-tasks.json --completion-check .qa-agent/current/completion-check.json --risk-analysis .qa-agent/current/risk-analysis.json --code-review .qa-agent/current/code-review.json --output .qa-agent/reports/latest-report.html
ming-qa assert-report-freshness --report .qa-agent/reports/latest-report.html --cases .qa-agent/current/test-cases.json --spec-tasks .qa-agent/current/test-spec-tasks.json --completion-check .qa-agent/current/completion-check.json --risk-analysis .qa-agent/current/risk-analysis.json --code-review .qa-agent/current/code-review.json --output .qa-agent/current/report-freshness-check.json
ming-qa assert-readiness --completion-check .qa-agent/current/completion-check.json --code-review .qa-agent/current/code-review.json --evidence-integrity-check .qa-agent/current/evidence-integrity-check.json --report .qa-agent/reports/latest-report.html --report-freshness-check .qa-agent/current/report-freshness-check.json --output .qa-agent/current/readiness-check.json
ming-qa render-report --cases .qa-agent/current/test-cases.json --run .qa-agent/current/latest-run.json --spec-tasks .qa-agent/current/test-spec-tasks.json --completion-check .qa-agent/current/completion-check.json --risk-analysis .qa-agent/current/risk-analysis.json --code-review .qa-agent/current/code-review.json --readiness-check .qa-agent/current/readiness-check.json --output .qa-agent/reports/latest-report.html
ming-qa check-mojibake .qa-agent/reports/latest-report.html .qa-agent/current/completion-check.json .qa-agent/current/readiness-check.json --strict
# 归档报告（手动生成时间戳副本）：
python -c "import shutil,datetime;ts=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');shutil.copy2('.qa-agent/reports/latest-report.html',f'.qa-agent/reports/{module}-{runType}-{ts}.html')"
```

`assert-completion` / `assert-code-review` / `assert-readiness` 通过后，用 `render-report` 渲染
`latest-report.html`，再用 `python shutil.copy2` 生成带时间戳的归档副本。
