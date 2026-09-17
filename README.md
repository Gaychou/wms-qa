# QA Agent

[中文文档](README.zh-CN.md) | English

An end-to-end QA acceptance orchestrator for coding agents. It walks a feature
through context gathering, risk analysis, test-case design, script generation,
execution, code review, and a final readiness verdict — pausing exactly once,
for you to approve the test cases.

Distributed as an **Agent Skill**, so it works with Claude Code, Codex, Cursor,
and any other agent that reads the `SKILL.md` format.

```
context → risk analysis → test case design → 【you confirm】 → scripts → run & repair → code review → report
```

## Install

```bash
# Option 1 (recommended): cross-agent, works with 40+ agents
npx skills add mingdui/ming-qa -g

# Option 2: Claude Code plugin marketplace
/plugin marketplace add mingdui/ming-qa
/plugin install ming-qa@ming-qa

# Option 3: from source (offline / custom install location)
git clone https://github.com/mingdui/ming-qa.git
cd ming-qa/skills/quality-assurance-agent && ./install.sh --target claude
```

No shell profile is modified by any of these. See [docs/installation.md](docs/installation.md)
for how to invoke the CLI and for troubleshooting.

<details>
<summary>Installing non-interactively (scripts / CI)</summary>

```bash
npx skills add mingdui/ming-qa --agent claude-code --yes \
  -s quality-assurance-agent -s qa-context-profiler -s qa-risk-analyzer \
  -s qa-testcase-designer -s qa-test-script-generator -s qa-test-runner \
  -s qa-code-reviewer -s qa-report-generator
```

- The agent is named **`claude-code`**, not `claude`（`claude` aborts with `Invalid agents`）.
- `--skill` takes one exact name at a time — no commas, no `*`. The CLI expands `*` as a
  **filesystem** glob against your current directory, so it fails with a confusing
  `No matching skills found for: AGENTS.md, src, …`. Repeat `-s` for each skill.

</details>

## Quick start

```bash
cd your-project

# Initialise: creates .qa-agent/, config templates, and the Playwright E2E setup
ming-qa init-project --repo . --agent claude     # claude / codex / both

# Fill in your secrets (git-ignored, never commit this)
#   .qa-agent/local/.env

# Environment check
ming-qa doctor --repo . --strict --check-services
```

Then, in your agent:

```
Use quality-assurance-agent to run acceptance testing on <your module>
```

The orchestrator pauses when the test cases are ready and waits for your
approval. Everything after that runs automatically.

Already-verified module? Just ask for a regression — existing cases and scripts
are reused.

## What it produces

Everything lands in `.qa-agent/` inside your project.

| Path | Contents | Survives `git clone` |
|---|---|---|
| `.qa-agent/cases/` | Approved long-term test cases | ✅ |
| `.qa-agent/spec-tasks/` | Use-case → script mapping | ✅ |
| `.qa-agent/reports/` | HTML reports | ✅ |
| `.qa-agent/current/` | This run's working artifacts | ❌ regenerated |
| `tests/api/<module>/` | Generated test scripts | ✅ |

## Requirements

- Python 3.9+ (stdlib only — no third-party runtime dependencies)
- Git
- Java 21 / Maven or Node.js 20+ in the target project, depending on scope

## Privacy

This tool ships with **no default external endpoints**. It will not contact any
service unless you configure one:

- LLM gateway — unset by default; multi-model review is skipped if unconfigured
- Report webhook — empty by default; no notifications, no network requests

See [docs/configuration.md](docs/configuration.md).

## Documentation

- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Architecture](docs/architecture.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## License

[MIT](LICENSE)
