# Staged QA Skill Architecture

## Purpose

Use one top-level `quality-assurance-agent` for user experience and seven focused stage skills for adherence, speed, reuse, and reduced drift.

## Stage Skills

| Stage | Skill | Owns | Must Not Do |
|---|---|---|---|
| 0 | `qa-context-profiler` | context, existing case index, environment/profile evidence | business cases, tests, readiness |
| 1 | `qa-risk-analyzer` | high-risk paths, required oracles, missing coverage | test code, product fixes, Ready decisions |
| 2 | `qa-testcase-designer` | Chinese business test cases, model review, confirmation page | test code, product fixes |
| 3 | `qa-test-script-generator` | spec tasks, coverage balance, mapped test files | execution pass/fail, readiness |
| 4 | `qa-test-runner` | execution, repair, evidence, completion gate | report rendering, code review, Ready decisions |
| 5 | `qa-code-reviewer` | independent code review, code-review gate | replace test evidence, report rendering |
| 6 | `qa-report-generator` | aggregate gates, render HTML report, readiness gate, final decision | re-run tests, code review, replace gate results |

## Handoff Rules

- Every stage reads previous `.qa-agent` artifacts instead of re-inventing scope.
- Long-lived knowledge is read from `.qa-agent/config`, `.qa-agent/cases`, `.qa-agent/profiles`, and `.qa-agent/risk-rules`; current-run evidence is written to `.qa-agent/current`, `.qa-agent/runs`, and `.qa-agent/reports`.
- The only human gate is confirmation of `test-cases.html` / `test-cases.json`.
- Confirmed cases must be promoted from `.qa-agent/current/test-cases.json` to `.qa-agent/cases/<module>.json`.
- P0/P1 risks must map to business cases and spec-task `oracle` / `assertions`, or become open questions/blockers.
- After confirmation, stages continue automatically until Ready, Not Ready, or Incomplete.
- `completion-check.json` is the deterministic source for spec-task completion.
- `code-review.json` plus `code-review-check.json` is mandatory code review evidence.
- `readiness-check.json` is the final deterministic source for Ready/Not Ready/Incomplete language.
- Existing tests can satisfy tasks only when mapped to exact file, test name, command, assertions, oracle, and evidence.
- Runner must classify every failure from local evidence, repair the smallest root cause, rerun the targeted scope, and only then widen the scope or escalate.

## Drift Prevention

- Context/profile separates environment checks from business behavior.
- Risk analyzer forces bug-hunting hypotheses before cases are written.
- Case designer cannot write scripts.
- Script generator cannot mark tasks passed.
- Runner cannot call Ready, cannot render the final report, and cannot hand off an actionable test/product/environment failure to the user before one repair pass.
- Code reviewer cannot override missing completion evidence or render the final report.
- Report generator cannot re-run tests or review code; it only aggregates existing gate artifacts.

## Maintenance Rules (Skill Sync)

当以下变更发生时，必须检查并同步更新受影响的子 skill 文件：

| 变更类型 | 检查清单 |
|---|---|
| `qa_agent.py` 新增 CLI 参数 | 主 skill "CLI 命令参考"章节 + 对应阶段的子 skill "Required Flow"（注明使用场景） |
| 新增通用工具命令（如 run-with-env、safe-write-json、manifest） | 主 skill "CLI 命令参考"章节 |
| 修改门禁/产物 schema | `references/spec-task-planning.md`、`references/quality-gates.md` |
| 修改各阶段的职责边界 | `references/stage-skills.md`（本文件）+ 对应的子 skill "你的定位"章节 |

**关键原则**：CLI 命令语法只在主 skill 维护一次。子 skill 不重复维护命令语法，但必须在 "Required Flow" 中明确：
- **什么时候**用哪个参数（如验收场景必须带 `--module`）
- **为什么**要这样用（不这样用的后果）
- 和上下游 skill 的**交接约定**
