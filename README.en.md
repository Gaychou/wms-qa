# QA Agent

[中文](README.md) | English

An end-to-end QA acceptance orchestrator for coding agents, distributed as an
**Agent Skill**. Works with Claude Code, Codex, Cursor, and any other agent that
reads the `SKILL.md` format. It walks a feature through context gathering, risk
analysis, test-case design, script generation, execution, code review, and a
final readiness verdict — **pausing exactly once**, for you to approve the cases.

```
context → risk analysis → test case design → 【you confirm】 → scripts → run & repair → code review → report
```

## Install

```bash
# Cross-agent (recommended): installs once, links into every detected agent
npx skills add mingdui/ming-qa -g -y

# Claude Code plugin marketplace
/plugin marketplace add mingdui/ming-qa
/plugin install ming-qa@ming-qa

# From source (offline / custom location)
git clone https://github.com/mingdui/ming-qa.git
cd ming-qa/skills/quality-assurance-agent && ./install.sh --target claude-code
```

`-g` installs at user level for all projects (omit it for the current project only);
`-y` installs all 8 skills in one go. More in the [installation docs](docs/installation.md).

## Quick start

Once installed there is no command to type. In your agent, just say:

```
Use quality-assurance-agent to run acceptance testing on <your module>
```

The agent initialises the project, checks the environment, installs whatever
toolchain the scope needs — and stops only where you are actually required:

| It stops at | What you do |
|---|---|
| **Config** | Fill `.qa-agent/local/.env` from the checklist it prints (git-ignored). Only the test account is required. |
| **Case confirmation** | Review the generated test cases. The single mandatory human gate in the whole flow. |

Everything after that runs automatically: scripts, execution and repair, code
review, report.

## What it produces

Everything lands in `.qa-agent/` inside your project.

| Path | Contents | Survives `git clone` |
|---|---|---|
| `.qa-agent/cases/` | Approved long-term test cases | ✅ |
| `.qa-agent/spec-tasks/` | Use-case → script mapping | ✅ |
| `.qa-agent/config/` | Project QA configuration | ✅ |
| `.qa-agent/knowledge/` | Project knowledge base | ✅ |
| `.qa-agent/reports/` | HTML reports | ✅ |
| `.qa-agent/current/` | This run's working artifacts | ❌ regenerated |
| `.qa-agent/runs/` | Execution logs and evidence | ❌ |
| `.qa-agent/local/` | Local credentials | ❌ |
| `tests/api/<module>/` | Generated test scripts | ✅ |

## Data and network

The tool ships with no external endpoints. It only talks to the network once you
configure a destination:

- **LLM gateway** — for the optional multi-model cross review; skipped if unset
- **Report webhook** — for report quality alerts; no notifications if unset

Both are configured in [docs/configuration.md](docs/configuration.md).

## Requirements

- Python 3.9+ (stdlib only — no third-party runtime dependencies)
- Git
- Java 21 / Maven or Node.js 20+ in the target project, depending on scope

## Troubleshooting

| Symptom | Where to look |
|---|---|
| Won't install / environment errors / services won't start | [Installation](docs/installation.md) |
| What does this config option mean? | [Configuration](docs/configuration.md) |
| How are the stages and gates designed? | [Architecture](docs/architecture.md) |

**Running the CLI by hand** (usually while debugging): it lives at the skill's
`scripts/qa_agent.py`. Resolve the skill directory first, then use it:

```bash
QA_AGENT_DIR="${QA_AGENT_CLI:-$(dirname "$(find ~/.claude/skills ~/.agents/skills ~/.codex/skills .claude/skills .agents/skills .codex/skills -maxdepth 2 -name SKILL.md -path '*quality-assurance-agent/*' 2>/dev/null | head -1)")}"
python "$QA_AGENT_DIR/scripts/qa_agent.py" doctor --repo . --strict --check-services
```

## Contributing

[Contributing guide](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## License

[MIT](LICENSE)
