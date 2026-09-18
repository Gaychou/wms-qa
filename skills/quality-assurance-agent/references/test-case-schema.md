# Test Case Schema

`test-cases.json` is the canonical machine-readable business test-case file. It describes business operation points and operation paths, not test framework readiness.

Do not put pure tooling or environment checks in `cases`. Examples that belong outside `cases`: "Maven full suite passes", "Vitest can run", "Playwright Test Agents installed", "browser dependencies installed", "compile succeeds", "test files can be listed". Store those in quality-gate run evidence or `environmentChecks`.

## Language Policy

- Human-readable narrative must use Simplified Chinese: `metadata.requirement`, `assumptions`, `openQuestions`, `title`, `preconditions`, `steps`, `expected`, `businessActor`, `operationPath`, `businessStateBefore`, `businessAction`, `businessStateAfter`, `businessAssertions`, and `risk`.
- Product/domain terms may remain in their official form, for example `TikTok`, `Firebase`, `creatorId`, `REWARD_ISSUED`, `/api/creator/social-submissions`, `Playwright`, `Maven`, `Vitest`, `H5`, `Admin`, and exact UI labels or API fields.
- `source`, `traceability`, `implementation`, `command`, file paths, URLs, enum values, code symbols, account names, and raw evidence should stay exact and must not be translated if translation would reduce traceability.
- Existing cases keep stable IDs and execution history, but their narrative fields should be translated or rewritten into Chinese before rendering `test-cases.html` for confirmation.

## Root Shape

```json
{
  "version": "1.0",
  "metadata": {
    "project": "project-name",
    "requirement": "short requirement title",
    "baseBranch": "main",
    "generatedAt": "2026-07-23T00:00:00Z",
    "sourceRefs": ["docs/spec.md", "git diff"]
  },
  "assumptions": [],
  "openQuestions": [],
  "environmentChecks": [],
  "qualityGates": [],
  "cases": []
}
```

## Case Shape

Required fields:

- `id`: stable ID, for example `TC-P0-001`.
- `title`: concise scenario title.
- `priority`: `P0`, `P1`, `P2`, or `P3`.
- `layer`: one of `frontend-unit`, `backend-unit`, `api`, `integration`, `e2e`, `manual`, or `unknown`.
- `type`: functional, regression, boundary, exception, security, permission, compatibility, performance, data, or visual.
- `module`: product or code module.
- `source`: facts that justify the case.
- `preconditions`: list of required state/data.
- `steps`: list of actions or calls.
- `expected`: list of observable assertions.
- `data`: test data requirements.
- `automation`: `automated`, `candidate`, `manual`, or `blocked`.
- `status`: `draft`, `confirmed`, `implemented`, `passed`, `failed`, `skipped`, or `blocked`.

Recommended fields:

- `businessActor`: user, admin, external system, scheduler, queue consumer, callback sender, or other business actor.
- `operationPath`: concise business operation path, for example `素材发布 -> material_publish -> 第三方 500 -> 告警`.
- `businessStateBefore`: relevant business state before the operation.
- `businessAction`: the concrete business action under test.
- `businessStateAfter`: expected business state after the operation.
- `businessAssertions`: business assertions independent of the chosen test framework.
- `risk`: business risk if uncovered.
- `riskIds`: risk IDs this case covers, for example `["RISK-P0-001", "RISK-P1-003"]`.
  This is the **only** source the coverage projection reads. A risk that is mentioned
  anywhere in the case but not listed here does not count as covered — the report will
  show it as a gap. Leaving this empty while the risk is genuinely covered produces a
  report that contradicts reality.
- `tags`: free-form tags such as `auth`, `payment`, `contract`, `playwright`.
- `owner`: frontend, backend, fullstack, qa, or unknown.
- `traceability`: requirement IDs, issue IDs, code paths, API paths. Mixed content is
  allowed and is **not** read as risk links — an entry only counts as a risk link when it
  matches the risk ID form (`RISK-<priority>-<number>`). Prefer `riskIds` for that.
- `implementation`: files, commands, and assertions after implementation.
- `result`: last execution result, log path, screenshots, trace, and error summary.

## Priority Rules

- `P0`: asset loss, data inconsistency, authorization bypass, main flow blockage, state corruption, settlement/payment/reward calculation errors.
- `P1`: core business rules and important regression flows.
- `P2`: boundary values, invalid inputs, retry/timeout, non-critical exceptions.
- `P3`: display details, copy, visual polish, non-blocking compatibility.

## Validation Rules

- Every case must have at least one source reference.
- Every automated/candidate case must have deterministic expected assertions.
- Every case must describe a business actor and operation path, either with `businessActor`/`operationPath` or clearly in `steps`.
- Narrative fields should be Simplified Chinese except exact product/domain terms and technical identifiers. If a long narrative field is entirely English, rewrite it before user confirmation.
- Case titles must describe business behavior. If a title is only a tool/check phrase such as `Maven 全量通过`, `Playwright 安装成功`, `Vitest 可运行`, `node:test 全量`, `compile 成功`, or `测试文件可枚举`, move it to `qualityGates` or `environmentChecks`.
- Do not use uncertain expected values such as `200/400`; record an open question instead.
- Do not duplicate cases unless they validate different layers or different failure modes.

## Quality Gate Shape

Use this optional root field for technical gate evidence that supports business cases but is not itself a business case.

```json
{
  "id": "QG-BACKEND-MAVEN",
  "name": "Backend Maven full suite",
  "category": "unit|api|integration|e2e|build|environment|review",
  "command": "cd your-project-backend && mvn -q test -DskipITs",
  "status": "passed|failed|skipped|blocked",
  "summary": "520 tests, 0 failures, 0 errors, 5 skipped",
  "artifacts": ["your-project-backend/target/surefire-reports"],
  "supportsCases": ["TC-P1-001"]
}
```

## Environment Check Shape

Use this optional root field for tool and dependency readiness.

```json
{
  "id": "ENV-PLAYWRIGHT-AGENTS",
  "name": "Playwright Test Agents installed",
  "status": "passed|failed|skipped|blocked",
  "detail": ".claude/agents/playwright-test-generator.md found",
  "requiredFor": ["e2e"]
}
```
