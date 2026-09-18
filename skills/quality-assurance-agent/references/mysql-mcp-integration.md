# MySQL MCP Integration

Use this reference when a target repository contains `.mcp.json`, declares `mysql_mcp`, runs real-local E2E, or needs test database seed/verify/cleanup.

## Rules

- Read DB MCP settings only from the target repo `.mcp.json`; do not invent host, user, password, database, or command arguments.
- `init-project --install-mysql-mcp` 自动从 `.env` 生成数据库凭证，并从 `.mcp.json` 为 Codex 生成 `.codex/config.toml`。不需要手动创建任何文件。
- 数据库凭证从 `.qa-agent/local/.env` 的 `QA_MYSQL_HOST/PORT/USER/PASS/DATABASE` 变量自动读取。
- 不要在终端输出、JSON、日志、报告和总结中暴露数据库主机、用户名、密码等敏感信息。
- MCP server 工具（`mcp__mysql_mcp__*`）可能需要重启 Agent 会话后才能加载，这不是安装失败。

## QA Usage

- Treat MySQL MCP as a G0 environment capability, not a business test case. Do not put "MySQL MCP installed" or "DB connection succeeds" into `test-cases.json`.
- Use DB access to prepare and verify business operation paths:
  - `seed`: create unique QA data before E2E, preferably with a prefix such as `QA_AGENT_<timestamp>`.
  - `verify`: confirm business state changes, audit status, settlement/reward records, notification records, or cleanup side effects after UI/API actions.
  - `cleanup`: remove or mark QA data after the run when safe.
- Store DB readiness and connection evidence in `environmentChecks` or `qualityGates`. Store business outcomes in the corresponding business case result.
- If DB access is unavailable, mark affected business cases `blocked` with the missing environment reason; do not convert the environment failure into a fake business case.

## Commands

```powershell
python "$QA_AGENT_DIR/scripts/qa_agent.py"install-mysql-mcp --repo . --verify
python "$QA_AGENT_DIR/scripts/qa_agent.py"init-project --repo . --install-mysql-mcp --verify-mysql-mcp
python "$QA_AGENT_DIR/scripts/qa_agent.py"doctor --repo . --strict --verify-mysql-mcp --json .qa-agent/current/environment-checks.json
```

`init-project --install-mysql-mcp` 自动做两件事：从 `.env` 生成 `.mysql-mcp/credentials`，从 `.mcp.json` 生成 `.codex/config.toml`（供 Codex 使用）。前提是 `.env` 里有 `QA_MYSQL_*` 变量且 `.mcp.json` 里声明了 `mcpServers.mysql_mcp`。条件不足则静默跳过。
