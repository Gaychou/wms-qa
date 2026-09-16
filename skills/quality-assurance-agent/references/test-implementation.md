# Test Implementation Guide

## Stack Detection

Inspect manifests before writing tests:

- `package.json`: npm scripts, Vitest/Jest/Playwright/Cypress, Next.js, React, Vue, Angular.
- `pom.xml`: Maven, Spring Boot, JUnit, Surefire/Failsafe.
- `build.gradle` or `build.gradle.kts`: Gradle and JVM tests.
- `pytest.ini`, `pyproject.toml`: Python pytest.
- Existing `src/test`, `tests`, `specs`, `__tests__`, `*.spec.*`, `*.test.*`.

Before executing gates, build a project test profile from real files. If a command uses a glob, verify that the glob matches files. On Windows PowerShell, expand Node `node:test` globs into an explicit file list before running the command.

## Implementation Order

1. Read existing tests and helpers for the target module.
2. Confirm the case is a business operation path, not a tool/readiness check.
3. Map each confirmed case to the narrowest reliable test layer.
4. Add tests using existing style and fixtures.
5. Run list/compile checks before full execution when supported.
6. Execute targeted tests first, then gate-level commands.

## Layer Guidance

- Unit tests: algorithms, reducers, composables/hooks, validators, state machines, reward/price calculations, permission helpers.
- API tests: endpoints, request/response schema, auth, validation, idempotency, error codes.
- Integration tests: service + database, message queues, scheduled jobs, callbacks, multi-component behavior.
- E2E tests: user-visible flows, navigation, form submission, cross-system handoffs.

## E2E Rules

- If `.claude/agents/playwright-test-*.md`, `specs/`, or `playwright-report/` exists, read `playwright-agent-integration.md` before adding or healing Playwright tests.
- Reuse login/auth setup and page helpers.
- Use unique timestamped test data.
- For state-changing actions, wait for and assert the real API response.
- Do not rely on historical data counts.
- Use stable selectors or product text verified from code.
- If environment is unavailable, run compile/list checks and report that runtime execution was blocked.

## Backend Rules

- Read production method signatures before writing tests.
- Verify enum and constant values from code, not stale docs.
- Prefer service-level tests for state machines, scheduled jobs, callbacks, retries, and concurrency.
- For Maven, targeted commands usually look like `mvn test -Dtest=ClassName`.
- On Windows PowerShell, quote multi-class selectors: `mvn -q "-Dtest=ClassA,ClassB" test`.
- After full Maven runs, parse `target/surefire-reports/TEST-*.xml` for the authoritative test summary.

## Known Monorepo Pattern: ai-content-creation-platform

- Admin unit: `your-project-admin/src/**/*.test.js`, run `cd your-project-admin && npm run test -- --run`.
- Creator H5 unit: `your-project-h5/tests/*.test.mjs` and optional `src/**/*.test.ts`; run explicit files with `node --loader ./tests/typescript-loader.mjs --test ...` when the loader exports `load()`.
- Backend JUnit: `your-project-backend/src/test/java`, run `cd your-project-backend && mvn -q test -DskipITs`; use `mvn -q -Dtest=<ClassName> test` for targeted repair.
- Build/compile evidence is separate from unit/integration evidence: H5 `npm run build` and backend `mvn -q -DskipTests compile` do not replace tests.
