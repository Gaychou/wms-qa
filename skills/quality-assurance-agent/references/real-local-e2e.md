# Real-Local E2E

Use this reference when QA runs against local H5/Admin/Backend services and a test database.

## Required Sequence

1. Run `check-local-stack --repo . --json .qa-agent/current/local-stack-check.json` before browser automation.
2. Execute browser flows without API route mocks for the primary business path.
3. Store raw evidence in `.qa-agent/runs/<timestamp>/`: screenshots, request/console JSON, DB verification JSON, and supplemental logs.
4. Summarize the run as `real-local-e2e-summary.json`.
5. Render with `render-real-local-e2e-report --run ... --normalized-json ... --output ...`.
6. Run `check-mojibake --strict` on the report and normalized JSON.

## Evidence Contract

The summary should include:

- `status`: `passed`, `failed`, or `blocked`.
- `environment`: H5/Admin/Backend base URLs and mode.
- `realLocalFlow.h5`: H5 browser steps, console events, request events, submit response, and status.
- `realLocalFlow.admin`: Admin browser steps, console events, request events, review response, and status.
- `realLocalFlow.dbFinal`: final DB state needed to prove business consistency.
- `existingPlaywrightSuites`: mock-backed or supplemental suites, clearly marked as supplemental.
- `artifacts`: absolute paths to raw evidence.
- `notes`: honest execution notes and limitations.

## Noise Classification

Classify browser events before deciding readiness:

- `blocking-error`: console/runtime issue that blocks the business path.
- `business-api-error`: failed `/api/` request or 5xx response tied to the business path.
- `dev-server-noise`: Vite/Next HMR, dev WebSocket, hot reload transport.
- `third-party-resource-noise`: CDN/media/static resource aborts that do not affect assertions.
- `non-blocking-warning`: observed fetch warning that is later recovered or not tied to the asserted path.

## Readiness

- `Ready`: main real-local flow passed, DB evidence passed, and no recorded gaps.
- `Conditionally Ready`: main flow passed but known gaps remain, such as test-profile login, QA seed data, or mock-backed supplemental suites.
- `Not Ready`: main flow failed, DB verification failed, local stack blocked, or blocking browser/API errors remain.

## Boundaries

Agent optimization should improve orchestration, evidence, classification, reports, and readiness. Do not change product code unless the user explicitly asks for product fixes after the Agent has classified the issue.
