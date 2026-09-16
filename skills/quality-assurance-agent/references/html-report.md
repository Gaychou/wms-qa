# HTML Report

The HTML report should be a self-contained artifact that can be opened without a server.

## Sections

- Executive summary: overall status, gates, pass/fail/skip counts.
- Requirement review: facts, assumptions, open questions.
- Business test-case matrix: priority, business actor, operation path, layer mapping, automation status, execution result.
- Test-case confirmation summary: the same cases should also be printed in Chinese in chat immediately after `render-cases`.
- Risk analysis: P0/P1/P2/P3 risk summary, affected files, coverage gaps, and required oracles.
- Quality gate and environment matrix: Maven/Vitest/node:test/Playwright/build/compile/tool checks, command results, durations, and artifacts.
- Completion gate: `assert-completion` status, enforced priorities, unconfirmed/under-minimum cases, missing mapping/evidence, unimplemented/unexecuted/blocked/deferred/skipped/failed spec-task counts, and first actionable next task IDs when incomplete.
- Multi-model review: models used, findings accepted/rejected, failed model calls.
- Execution evidence: commands, durations, exit codes, artifact paths.
- Repair loop: failure classification, root cause, fixes, commit IDs.
- Code review: findings and residual risks.
- Readiness gate: `assert-readiness` status, final decision, and blocking findings.
- Final decision: ready, conditionally ready, or not ready.
- Real-local E2E reports should include local service readiness, H5/Admin browser steps, DB final state, screenshot/log artifacts, console/request noise classification, and a readiness decision.

## Visual Rules

- Use dense tables for engineering details.
- Keep business coverage and technical gate readiness visually separate.
- Highlight P0/P1 and failed gates.
- Preserve raw evidence paths and command names.
- Never display invented metrics. Missing metrics should show `N/A`.
- Never infer full business coverage from existing quality gates. Pass `--completion-check .qa-agent/current/completion-check.json` to `render-report`; if `completion-check.json` failed or is missing after spec-task generation, show `Incomplete` and list the missing spec-task evidence.
- Pass `--risk-analysis .qa-agent/current/risk-analysis.json`, `--code-review .qa-agent/current/code-review.json`, and `--readiness-check .qa-agent/current/readiness-check.json` when those artifacts exist.
- Test-case narrative in JSON/HTML reports must be Simplified Chinese except exact product/domain terms, code identifiers, API paths, enum values, commands, URLs, and raw evidence.
- JSON and HTML artifacts must be UTF-8 and human-readable. If Chinese text is mojibake, rewrite the artifact before continuing.
- Run `check-mojibake --strict` on generated reports and case-confirmation pages, or rely on the default `render-report`/`render-cases` post-render check. Use `--allow-mojibake` only when preserving known raw third-party evidence is more important than failing the report.
- Use `render-real-local-e2e-report` for `real-local-e2e-summary.json` instead of ad-hoc HTML scripts.

## 报告命名约定

所有 QA 报告使用 **方案 A：前缀分层** 命名：

```
reports/
├── latest-report.html                                   ← 始终指向最后一次运行（覆盖）
├── order-acceptance-20260730-191801.html              ← 首次验收
├── order-regression-20260731-123840.html              ← 回归
├── order-incremental-20260730-195222.html             ← 增量
├── battle-acceptance-20260801-140000.html
└── ...
```

**格式**：`{module}-{runType}-{YYYYMMDD-HHMMSS}.html`

| 字段 | 取值 |
|------|------|
| `module` | `order`, `battle`, `auth` ... |
| `runType` | `acceptance`（首次）/ `regression`（回归）/ `incremental`（增量） |

渲染时通过 `--module <模块名> --run-type <类型>` 自动生成归档副本。
