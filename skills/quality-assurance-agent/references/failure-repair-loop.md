# Failure Repair Loop

## Classification

For every failure, classify before editing:

- Product bug: test assertion matches current requirement and production code violates it.
- Obsolete test: test assertion reflects old requirement and production code matches current requirement.
- Test bug: test setup, data, selector, mock, or timing is wrong.
- Environment issue: missing service, credentials, network, browser, database, or dependency.
- Requirement ambiguity: no authoritative expected result exists.

This classification is done by the agent from local evidence first. Do not ask the user to choose between test bug, product bug, or environment issue unless the local evidence still cannot disambiguate the root cause after one repair pass.

Also record whether the failure happened in:

- Business assertion: a confirmed operation path produced the wrong business result.
- Quality gate: compile/build/test command failed before or around business assertions.
- Environment readiness: tools, browsers, services, credentials, encoding, or test discovery blocked execution.

Only business-assertion failures should make a business case `failed`. Quality-gate or environment failures that prevent execution should make affected business cases `blocked` and should update the quality/environment evidence instead.

## Three-Way Comparison

Always compare:

```text
test assertion <-> current requirement/spec <-> production implementation
```

Do not fix code based on a failing assertion alone.

For obsolete-test decisions, check recent history before editing:

```text
git log --oneline -- <file>
git show <relevant-commit> -- <file>
```

Use history to distinguish "test assertion is stale" from "production code regressed from a business/API contract".

## Repair Rules

- Make the smallest change that directly addresses the root cause.
- Avoid broad refactors unless the root cause cannot be fixed safely otherwise.
- Re-run the targeted failing tests after each fix.
- Then re-run the relevant quality gate.
- Commit product-code fixes atomically.
- Stop after `maxRepairLoops` and report remaining failures if unresolved.

Default routing:

1. **Test bug** -> fix the test, rerun the exact failing scope.
2. **Product bug** -> fix code, rerun the exact failing scope, then broaden if needed.
3. **Environment issue** -> repair the environment/service/dependency, then rerun.
4. **Requirement ambiguity** -> escalate only when the expected result cannot be derived from authoritative sources.

If the same failure class repeats after one repair attempt, treat it as a blocker and report the exact evidence chain instead of looping the same explanation.

## Commit Guidance

- Test additions: `test: 添加 <模块> 测试覆盖`
- Product fixes: `fix: 修复 <问题>`
- Tooling/config: `chore: 更新 <工具或配置>`

Each commit body should include:

- Root cause.
- Fix summary.
- Verification command and result.
