# QA Agent Workflow

## Phase 0: First-Time Project Setup

For a new repo, run the one-command setup first:

```bash
ming-qa init-project --repo .
```

The user fills `.qa-agent/local/.env` only. Validate required local values with:

```bash
ming-qa doctor --repo . --strict --check-services
```

Do not continue to model review or E2E when required API keys, account env vars, or required service URLs are missing.

Only use these explicit installers when the user wants external tool config changed:

```bash
ming-qa init-project --repo . --install-playwright-agents --install-mysql-mcp --verify-mysql-mcp
```

## Phase 0.5: Scope Lock And Precheck Confirmation

Before business case design, lock the following from local evidence or one bundled user clarification:

1. Current scope: requirement, module, diff, branch, PR, or business flow.
2. Business main path: the critical journey that must be validated end to end.
3. Blockers: environment, data, access, or product blockers that prevent progress.
4. Oracles: the visible business facts that prove success or failure.

This is the only allowed upfront clarification pass. If scope, main path, blocker, or oracle is still unclear after context review and environment precheck, ask the user once in a bundled way. Do not wait until case confirmation or Playwright execution to resolve these basics.


## Phase A: Context And Requirement Review

1. Collect context from:
   - User prompt and linked requirement documents.
   - Product specs, OpenAPI/Swagger files, API docs, README, AGENTS/CLAUDE rules.
   - Source code that implements or calls the requested behavior.
   - Existing tests and test helpers.
   - `git diff` against the base branch.
2. Build a requirement review:
   - Facts confirmed from requirements or code.
   - Risks ranked by business impact.
   - Ambiguities and missing acceptance criteria.
   - Code-confirmed answers for initially unclear points.
   - Unresolved questions for user confirmation.
3. If scope, business main path, blocker, or oracle is still ambiguous, resolve it in Phase 0.5 before generating cases.
4. Do not generate executable tests before unresolved test-oracle questions are recorded.

## Phase B: Test-Case Design

Before generating new cases, run `index-existing-cases` and inspect:

- Existing business `test-cases*.json` files.
- Existing `test-spec-tasks*.json` files.
- Existing project test files and discovered test symbols.

Stable modules must not start from a blank slate. Reuse matching existing business cases and tests first. Generate only delta cases for uncovered changed behavior, missing boundary paths, or missing risk paths. If a new model-generated case matches an existing case, preserve the existing case identity and execution history.

Generate `test-cases.json` using `references/test-case-schema.md`.

Language requirement: write all human-readable business case narrative in Simplified Chinese, including titles, preconditions, steps, expected results, business actors, operation paths, business states, business assertions, risks, assumptions, and open questions. Keep product/domain terms, API paths, code identifiers, enum values, commands, URLs, file paths, and raw source evidence unchanged. Existing English cases may keep their IDs/history, but rewrite narrative fields into Chinese before user confirmation.

The test-case object is the business operation point or operation path. Use cases must be phrased in business language first, then mapped to unit/API/integration/E2E execution. Do not create test cases for tool readiness, framework installation, compile/build checks, or "can list tests"; record those as quality gates or environment checks.

Coverage must include:

- P0 main flows and asset/data consistency risks.
- P1 core business rules.
- P2 boundary and exception paths.
- P3 copy, display, and low-risk UI details.
- Historical defects and regression scenarios when available.
- Security and authorization checks for sensitive flows.
- Data isolation and cleanup strategy.

Each generated case should make the business path explicit:

- Business actor: user/admin/external callback/scheduler/consumer/system.
- Operation path: ordered business actions and system transitions.
- Business state before/after.
- Business assertions independent of the test framework.
- Execution mapping: the unit/API/integration/E2E layer that can verify the business assertion.

Render `test-cases.html` for human confirmation.

Recommended deterministic sequence:

```bash
ming-qa index-existing-cases --repo . --output .qa-agent/current/existing-case-index.json
# Generate candidate gaps as .qa-agent/current/test-cases.generated.json
ming-qa merge-existing-cases --repo . --generated .qa-agent/current/test-cases.generated.json --existing-index .qa-agent/current/existing-case-index.json --output .qa-agent/current/test-cases.json
```

After rendering, print a concise Chinese test-case summary table in the chat. Do not only provide artifact paths; the user must see the cases that are being confirmed.

## Phase C: Multi-Model Review

Run 3 model reviews with:

- `gpt-5.4`
- `claude-sonnet-5`
- `deepseek-v4-pro`

Each model reviews gaps, wrong assertions, duplicate cases, priority errors, and missing high-risk scenarios. The main session must synthesize the review reports and update `test-cases.json`; do not blindly accept model output.

## Phase D: Human Confirmation

Ask the user to confirm, delete, or add test-case directions. This is the mandatory business gate after the upfront scope-lock pass. After confirmation, continue automatically through implementation, execution, repair, reporting, and code review.

After confirmation, persist reusable business cases:

```bash
ming-qa promote-cases --cases .qa-agent/current/test-cases.json --repo . --module <module-or-flow>
```

## Phase E: Test Split And Implementation

Split test cases into:

- Frontend unit tests.
- Backend unit tests.
- API tests.
- Integration tests.
- E2E tests.

Detect stack from manifests and existing tests. Prefer existing test frameworks and helpers. Only add a new framework when no suitable framework exists and the config allows it.

After the user confirms business cases, expand them into `test-spec-tasks.json` before writing test code. The spec task list is the execution backlog for implementation, not another user-confirmation artifact. Each task must include source case ID, layer, target project/file, test name, assertions, command, implementation status, execution status, and evidence. Human-readable task names and assertions should follow the same Chinese-first language policy as business cases.

Default coverage balance:

- Unit: about 60%.
- Integration: about 20%.
- API: about 15%.
- E2E: about 5%.

Default minimum spec tasks per business case:

- P0: 8.
- P1: 5.
- P2: 3.
- P3: 1.

Run `coverage-balance --strict` before writing tests. If the balance fails, repair the task plan instead of hiding the gap in the report.

Before executing commands, verify the project test profile: test roots exist, globs match files, package scripts exist, and Playwright can list tests. Treat "no tests found" as skipped/blocked quality-gate/environment evidence, not as a passed business case.

Maintain two separate matrices:

- Business coverage matrix: confirmed business cases and their execution mapping.
- Spec task matrix: one row per implementation task, linked to a source business case and target test file.
- Quality/environment matrix: Maven/Vitest/node:test/Playwright/build/compile/tool checks and their artifacts.

The spec task matrix is a work queue, not a documentation artifact. A model must keep implementing/executing the next P0/P1 task batch until each task reaches a real terminal state or has a recorded blocker/deferral accepted by the user.

### E.1 Playwright Test Agent Routing

When the implementation backlog contains E2E work and the repository has Playwright Test Agent assets or needs them:

1. **Planner** — use the Playwright Planner for new surfaces, new cross-system flows, or any E2E area whose user journey is not yet mapped. Produce a markdown plan before coding the spec.
2. **Generator** — after the user confirms the business case or the plan item, use the Playwright Generator to create one spec file per scenario with step comments and stable locators.
3. **Healer** — when a Playwright spec fails, route the failing test to the Playwright Healer first. Classify and fix selector, timing, data, environment, or product issues before weakening assertions.
4. **Stable reruns** — if the E2E suite is already implemented and only needs a clean rerun or report refresh, skip planner/generator/healer unless the scope changed or a failure appears.

## Phase F: Execution And Repair Loop

Run tests, update result fields, and diagnose failures. Fix minimal root causes. Repeat until all gates pass or `maxRepairLoops` is reached. Default is 5.

For every failure, record the business case(s) affected and the technical gate that failed. If the failure is only environment/tool readiness and no business assertion ran, mark the business case `blocked`, not `failed`.

Failure handling order:

1. Classify from local evidence before editing.
2. Prefer repairing the narrowest artifact that explains the failure.
3. Re-run the exact failing scope before expanding the blast radius.
4. Escalate only when the same failure class repeats after one repair attempt or the evidence is genuinely ambiguous.

User escalation is the last resort, not the default path. Do not ask the user to decide whether a failure is a test bug, product bug, or environment issue when the evidence already points to one class.

Each product-code fix must be committed atomically:

- One root cause per commit.
- Include tests or evidence in the same commit when practical.
- Do not mix unrelated refactors.

## Phase G: Reporting And Code Review

Before reporting, run `assert-completion` against `test-cases.json` and `test-spec-tasks.json`. If it fails, do not report full QA completion; continue the next task batch when possible. If context or environment prevents further progress, report `Incomplete` and list the next task IDs plus blockers.

Generate HTML report only after the completion gate result is recorded. Then run independent code review focused on:

- Architecture and layering compliance.
- Security vulnerabilities.
- Logic regressions.
- Missing or weak tests.
- Performance and reliability risks.

Output final QA report and code-review result. Final readiness must distinguish existing quality gates passed from full business/spec-task completion.
