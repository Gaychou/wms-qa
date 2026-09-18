# Spec Task Planning

Use this reference after business `test-cases.json` is confirmed and before writing test files.

## Principle

Business cases are for user confirmation. Spec tasks are for strict implementation. Do not write tests from vague intent; generate and validate the spec task backlog first.

## Commands

```bash
python "$QA_AGENT_DIR/scripts/qa_agent.py"generate-spec-tasks --cases .qa-agent/current/test-cases.json --repo . --output .qa-agent/current/test-spec-tasks.json
python "$QA_AGENT_DIR/scripts/qa_agent.py"coverage-balance --spec-tasks .qa-agent/current/test-spec-tasks.json --output .qa-agent/current/coverage-balance.json --strict
python "$QA_AGENT_DIR/scripts/qa_agent.py"assert-completion --cases .qa-agent/current/test-cases.json --spec-tasks .qa-agent/current/test-spec-tasks.json --output .qa-agent/current/completion-check.json
```

Useful tuning:

```bash
--ratio unit=0.60,integration=0.20,api=0.15,e2e=0.05
--min-specs-by-priority P0=8,P1=5,P2=3,P3=1
--max-e2e-per-case 2
```

## Spec Task Contract

Each task must include:

- `id`
- `sourceCaseId`
- `priority`
- `layer`: `unit`, `integration`, `api`, or `e2e`
- `focus`
- `targetProject`
- `targetFile`
- `testName`
- `businessActor`
- `operationPath`
- `assertions`
- `oracle`: `ui`, `api`, `db`, `sideEffects`, and `negativeAssertions`
- `command`
- `implementationStatus`
- `executionStatus`
- `evidence`

## Coverage Rules

- Unit tasks should be the largest group.
- Integration should be fewer than unit but more than E2E.
- API should cover contracts and authorization without duplicating all E2E flows.
- E2E should only cover high-risk main flows and a small number of critical branches.
- P0/P1 cases must not be under-specified. If `coverage-balance` fails, repair the spec task plan before implementation.
- P0/P1 risks from `.qa-agent/current/risk-analysis.json` must appear in task assertions or `oracle`; otherwise record an explicit blocker/open question.

## Execution Rules

- Implement tasks one by one.
- Update implementation and execution status after each task.
- Attach command output, screenshots, DB evidence, or report paths to non-empty `evidence`; a `passed` or `failed` task without evidence is not complete.
- Keep `targetFile`, `testName`, `command`, and `assertions` populated for every implemented task; existing suites only count when mapped to these exact fields.
- Keep `oracle` populated so execution knows what to assert at UI/API/DB/side-effect/negative levels.
- If a task is blocked, record the blocking dependency and do not mark the source business case as passed.
- Run `assert-completion` before final reporting. If it fails, the run is incomplete; continue with the next task batch instead of reporting full completion.
- Running an existing suite does not automatically satisfy generated tasks. A task is satisfied only when it records the matching existing or newly added test file, command, assertions, execution status, and evidence.
- Use `skipped` only for tests the runner actually skipped. Use `pending`/`not_started` for unimplemented tasks, `blocked` for environment/data/requirement blockers, and `explicitly_deferred` only when the user approved postponement.

## Completion Gate

`assert-completion` enforces P0/P1 by default:

- Fails when a P0/P1 case is still unconfirmed or has fewer than the configured minimum task count.
- Fails when a P0/P1 task is still `pending`, `not_started`, or `not-run`.
- Fails when a `passed`/`failed` task lacks mapping (`targetFile`, `testName`, `command`, `assertions`) or non-empty `evidence`.
- Fails when a P0/P1 task is `skipped`, `blocked`, or `deferred` unless the caller passes the matching `--allow-*` flag and the task includes non-empty `blocker`, `evidence` or `notes`, `owner`, and `nextAction`.
- Allows executed failures by default so the QA run can complete as `Not Ready`; pass `--fail-on-failed` when the target is ship readiness.
