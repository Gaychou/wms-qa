# QA Agent

[中文](README.md) | English

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
cd ming-qa/skills/quality-assurance-agent && ./install.sh --target claude-code
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

Once installed there is **no command to type**. In Claude Code / Codex, just say:

```
Use quality-assurance-agent to run acceptance testing on <your module>
```

The agent initialises the project, checks the environment, installs whatever
toolchain the scope needs — and stops only where you are actually required:

1. **Fill in config** — it tells you which values are missing and where they go
   (`.qa-agent/local/.env`, git-ignored). Only the test account is required; the
   LLM key is an optional cross-review enhancement and its stage is skipped without it.
2. **Confirm the test cases** — the single mandatory human gate in the whole flow.
3. Everything after that runs automatically: scripts, execution and repair, code
   review, report.

### Running the CLI by hand

The CLI lives at the skill's `scripts/qa_agent.py` and is **not distributed as a
PATH command**. Resolve the directory first:

```bash
QA_AGENT_DIR="${QA_AGENT_CLI:-$(dirname "$(find ~/.claude/skills ~/.agents/skills ~/.codex/skills .claude/skills .agents/skills .codex/skills -maxdepth 2 -name SKILL.md -path '*quality-assurance-agent/*' 2>/dev/null | head -1)")}"
python "$QA_AGENT_DIR/scripts/qa_agent.py" doctor --repo . --strict --check-services
```


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
