# Project Test Profile

Use this reference before writing `.qa-agent/config/qa-agent.config.yaml`, choosing commands, or classifying "no tests found" failures.

## Rules

- Detect real test roots and files before writing commands.
- Prefer explicit file lists when a shell may not expand globs, especially on Windows PowerShell.
- Treat build/compile checks as separate evidence from unit/integration tests.
- Treat Playwright agent installation, `playwright test --list`, Maven compile, Node/Vitest availability, and browser dependency checks as environment or quality-gate evidence. They are not business test cases.
- If no test files exist for a stack, mark that layer as `skipped` or `blocked` with a reason; do not report it as passed.
- For first-run audits, collect all feasible gate evidence before broad repair.
- On Windows PowerShell, quote Maven test selectors containing commas: `mvn -q "-Dtest=A,B" test`.
- Parse Maven Surefire XML reports after each backend full run; do not rely only on console output.
- Before writing Chinese JSON/HTML on Windows, force UTF-8 or write via Python UTF-8 APIs.

## 格式示例（请替换为你自己的项目）

下面是一个「后台 + H5 + 后端」三仓结构的填写示例，项目名均为占位符。
照此格式把你自己的真实测试入口写进 `.qa-agent/config/qa-agent.config.yaml`。

Admin（后台）：

- Root: `your-admin`
- Unit framework: Vitest
- Unit files: `src/**/*.test.js`
- Unit command: `cd your-admin && npm run test -- --run`
- E2E framework: Playwright
- E2E config: `your-admin/playwright.config.js`
- E2E test dir: `your-admin/e2e`
- E2E list command: `cd your-admin && npx playwright test --list`
- E2E runtime command: `cd your-admin && npx playwright test`

H5（移动端）：

- Root: `your-h5`
- Unit framework: Node `node:test`
- Unit files: `tests/*.test.mjs` and `src/**/*.test.ts`
- Loader: `./tests/typescript-loader.mjs` when present; if it exports `load()`, use Node's ESM `--loader` flag.
- Command strategy: expand files first, then run an explicit list:
  `cd your-h5 && node --loader ./tests/typescript-loader.mjs --test tests/yourRule.test.mjs`
- Build command: `cd your-h5 && npm run build`

Backend（后端）：

- Root: `your-backend`
- Test framework: Maven/JUnit
- Test dir: `src/test/java`
- Compile command: `cd your-backend && mvn -q -DskipTests compile`
- Full test command: `cd your-backend && mvn -q test -DskipITs`
- Targeted command: `cd your-backend && mvn -q -Dtest=<ClassName> test`
- Multi-class targeted command on PowerShell: `cd your-backend && mvn -q "-Dtest=<ClassA>,<ClassB>" test`
- Surefire summary command: `python "$QA_AGENT_DIR/scripts/qa_agent.py"summarize-surefire --reports your-backend/target/surefire-reports`
- Environment dependencies observed in full tests: test profile may initialize Redis, RocketMQ, object storage, and Spring scheduled components. Record missing or unavailable services as environment issues.

## Reporting

- Show the test-case summary table in chat after generating `test-cases.html`.
- Include the source test path and execution command in each case's `implementation`.
- Keep technical checks in the quality/environment section of the report; do not count them as business cases.
- Mark H5 unit tests as real unit tests when `tests/*.test.mjs` exists; do not replace them with `npm run build`.
- Mark Playwright separately as:
  - agents installed
  - tests listed
  - runtime executed
