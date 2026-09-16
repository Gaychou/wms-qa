# Code Review

## Review Scope

Review the final diff after tests and repairs:

- Architecture and layering compliance.
- Security: auth, authorization, injection, XSS, SSRF, secret leakage, unsafe deserialization, path traversal.
- Correctness: edge cases, null handling, race conditions, state transitions, off-by-one, timezone/date behavior.
- Risk coverage from `.qa-agent/current/risk-analysis.json`, especially P0/P1 permission, money/reward/settlement, state, async, and data consistency risks.
- Performance: N+1 queries, unbounded loops, memory leaks, excessive browser waits.
- Test quality: weak assertions, over-mocking, brittle selectors, missing negative paths.
- Maintainability: duplicated logic, stringly typed states, unclear ownership, hidden fallback behavior.

## Output Shape

```json
{
  "status": "passed|failed|blocked",
  "summary": "short result",
  "scope": {
    "files": [
      "src/main/java/com/example/Service.java"
    ],
    "description": "本次审查覆盖的业务模块"
  },
  "findings": [
    {
      "id": "CR-001",
      "severity": "P0|P1|P2|P3",
      "file": "path",
      "line": 1,
      "title": "issue",
      "evidence": "what proves it",
      "recommendation": "fix"
    }
  ],
  "residualRisks": [],
  "deferredFindings": [
    {
      "id": "CR-001",
      "deferredSince": "2026-07-30",
      "expiresAt": "2026-09-30",
      "reason": "既有代码行为，非本次引入，需独立改造",
      "owner": "开发团队",
      "riskIfNotFixed": "描述延后不修的风险"
    }
  ]
}
```

> ⚠️ `scope` **必须是对象** `{"files": [...], "description": "..."}`，不能是字符串。字符串 scope 会导致 `render-report` 崩溃，且会被证据完整性门禁判定为非法。
`deferredFindings` 中的 P0/P1 finding 在有效期内（`expiresAt` 未到）不会阻塞门禁。
`expiresAt` 可选——不设则不自动过期。

## Pass Criteria

Code review passes only when no unresolved P0/P1 findings remain. P2/P3 can remain if they are explicitly documented as residual risks.

After writing `.qa-agent/current/code-review.json`, run:

```bash
ming-qa assert-code-review --code-review .qa-agent/current/code-review.json --output .qa-agent/current/code-review-check.json
```

The final QA summary must use `assert-readiness`; Code review findings cannot override missing completion evidence.
