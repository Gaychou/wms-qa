# Existing Case Reuse

Use this reference before generating business cases for stable modules.

## Rule

The Agent must know existing cases and tests. If a matching case/test exists, execute or extend it. Generate new cases only for real gaps. Do not regenerate from scratch every run.

## Required Sequence

```bash
python "$QA_AGENT_DIR/scripts/qa_agent.py"index-existing-cases --repo . --output .qa-agent/current/existing-case-index.json
```

Then generate candidate gaps as `.qa-agent/current/test-cases.generated.json` and merge:

```bash
python "$QA_AGENT_DIR/scripts/qa_agent.py"merge-existing-cases --repo . --generated .qa-agent/current/test-cases.generated.json --existing-index .qa-agent/current/existing-case-index.json --output .qa-agent/current/test-cases.json
```

## Reuse Sources

The index includes:

- `.qa-agent/cases/**/*.json`
- `.qa-agent/spec-tasks/**/*.json`
- Legacy `.qa-agent/test-cases*.json` only when migrating old artifacts; do not create new root-level files.
- Stable `.qa-agent/spec-tasks/**/*.json` only when the project intentionally tracks reusable spec tasks; current-run tasks stay in `.qa-agent/current/`.
- Existing project test files from the detected test profile.

## Merge Behavior

- Match by module, business actor, and operation path when available.
- Fall back to module, actor, and title/steps.
- Existing matching cases win and keep their ID/history.
- Generated unmatched cases are appended as gap-fill cases.
- The merged file records `metadata.existingCaseReuse` and `reuseReport`.

## Execution Behavior

After merge:

- Execute existing matching test files first.
- Extend existing spec tasks when assertions are missing.
- Add new spec tasks only for uncovered business gaps.
- Report reused, extended, added, blocked, and skipped counts separately.
