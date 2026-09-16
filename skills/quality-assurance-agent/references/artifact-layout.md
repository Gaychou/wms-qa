# QA Agent Artifact Layout

Use this layout to keep `.qa-agent` predictable and gitignore-friendly. Do not scatter JSON/HTML files directly under `.qa-agent/`.

## Tracked Project Knowledge

Commit these directories when they contain sanitized project knowledge:

- `.qa-agent/config/`: project QA config, commands, thresholds, service variable names.
- `.qa-agent/cases/`: confirmed business test-case library, split by module or flow.
- `.qa-agent/profiles/`: stable test-path and stack profile.
- `.qa-agent/risk-rules/`: project-specific risk heuristics and business invariants.
- `.qa-agent/fixtures/`: only sanitized `*.example.*` fixtures.
- `.qa-agent/reports/`: generated HTML reports. Tracked so acceptance reports stay auditable across commits.

## Runtime Artifacts

Ignore these by default:

- `.qa-agent/current/`: current-run context, indexes, working cases, risk analysis, model review, spec tasks, and gate outputs.
- `.qa-agent/runs/`: command logs, browser traces, screenshots, videos, DB checks, and raw execution evidence.
- `.qa-agent/archive/`: optional manual QA audit snapshots.
- `.qa-agent/cache/` and `.qa-agent/tmp/`: temporary data.
- `.qa-agent/local/`: local-only `.env`, account references, and service URLs. Never commit real secrets.

## Playwright And Report Convention

When a repo uses Playwright Test Agents or any Playwright-based E2E flow, keep the artifact layout scoped and repeatable:

- Project-local Playwright HTML reports: `<project>/playwright-report/<scope>/index.html`
- Project-local Playwright raw E2E artifacts: `<project>/test-results/<scope>/`
- QA raw execution evidence: `.qa-agent/runs/<run-id>/playwright/<scope>/`
- QA scoped report bundle: `.qa-agent/reports/<scope>/<run-id>/`
- QA latest report pointer: `.qa-agent/reports/<scope>/latest-report.html`

Rules:

- The `<scope>` segment must be stable and human-readable, such as `admin-acceptance`, `cross-system`, or a named flow like `creator-withdrawal-handoff`.
- Never mix multiple scopes inside one report folder.
- Never leave generated HTML or raw trace artifacts at the `.qa-agent/` root.
- If a run is re-executed, write a new `<run-id>` folder instead of overwriting the previous raw evidence.

## Required Commands

Initialize a project:

```powershell
ming-qa init-project --repo .
```

Then fill only `.qa-agent/local/.env` and validate:

```powershell
ming-qa doctor --repo . --strict --check-services
```

Optional external setup remains explicit:

```powershell
ming-qa init-project --repo . --install-playwright-agents --install-mysql-mcp --verify-mysql-mcp
```

Persist confirmed cases after the only human gate:

```powershell
ming-qa promote-cases --cases .qa-agent/current/test-cases.json --repo . --module <module-or-flow>
```

## Gitignore Policy

Recommended root `.gitignore` snippet:

```gitignore
# QA Agent tracked knowledge, ignored runtime
.qa-agent/*
!.qa-agent/.gitignore
!.qa-agent/config/
!.qa-agent/config/**
!.qa-agent/cases/
!.qa-agent/cases/**
!.qa-agent/profiles/
!.qa-agent/profiles/**
!.qa-agent/risk-rules/
!.qa-agent/risk-rules/**
!.qa-agent/fixtures/
!.qa-agent/fixtures/**/*.example.*
!.qa-agent/reports/
!.qa-agent/reports/**
```

`init-project --root-gitignore` can append this snippet when the user wants the agent to manage it.
